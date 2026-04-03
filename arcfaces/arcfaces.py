# pyright: reportArgumentType=false
"""
Single-file ArcFace export extracted from:
https://github.com/VisoMasterFusion/VisoMaster-Fusion/blob/81eaf3cafe58b3a20a4c4044c060a00d68247291/app/processors/face_swappers.py

Constraints per request:
- No model management (no load/unload/download/verify).
- One function per ArcFace capability.
- No other helper functions/classes defined.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from importlib import metadata
from pathlib import Path

import numpy as np
import torch
from skimage import transform as trans
from torchvision.transforms import v2

__version__ = os.environ.get("ARCFACES_VERSION") or "0.0.0"
try:
    __version__ = metadata.version("arcfaces")
except metadata.PackageNotFoundError:
    pass


def arcface_recognize(
    ort_session,
    *,
    arcface_model_name: str,
    device: str,
    img: torch.Tensor,
    face_kps,
    similarity_type: str,
    arcface_dst,
):
    """
    Source reference:
    - https://github.com/VisoMasterFusion/VisoMaster-Fusion/blob/81eaf3cafe58b3a20a4c4044c060a00d68247291/app/processors/face_swappers.py#L99-L209

    Compute ArcFace embedding for standard ArcFace models using the same logic as FaceSwappers.recognize.

    Parameters
    ----------
    ort_session:
        Pre-loaded ONNX Runtime session for the ArcFace model (e.g., Inswapper128ArcFace, SimSwapArcFace).
        Must support .get_inputs(), .get_outputs(), .io_binding(), .run_with_iobinding().
    arcface_model_name:
        Used only to select the normalization branch:
        - "Inswapper128ArcFace"
        - "SimSwapArcFace"
        - anything else -> default branch
    device:
        Execution device string used by ORT IOBinding (e.g., "cpu", "cuda", "dml").
    img:
        Torch tensor image in CHW format (C,H,W). dtype may be uint8 or float.
    face_kps:
        5-point face landmarks (shape (5,2)).
    similarity_type:
        "Optimal", "Pearl", or anything else (default branch).
        NOTE: This exported function does NOT depend on app.processors.utils.faceutil;
        so the "Optimal" branch is not implemented and will raise.
    arcface_dst:
        Destination landmarks array used for alignment (shape (5,2)).

    Returns
    -------
    embedding: np.ndarray
        Flattened embedding vector.
    cropped_image: torch.Tensor
        Cropped/aligned face image as HWC tensor (112,112,3) in torch.
    """
    if similarity_type == "Optimal":
        raise NotImplementedError(
            'The "Optimal" branch depends on faceutil.warp_face_by_face_landmark_5 '
            "(app.processors.utils.faceutil), which is intentionally excluded."
        )

    if similarity_type == "Pearl":
        dst = np.array(arcface_dst, copy=True)
        dst[:, 0] += 8.0

        tform = trans.SimilarityTransform()
        tform.estimate(face_kps, dst)

        img = v2.functional.affine(
            img,
            tform.rotation * 57.2958, 
            (tform.translation[0], tform.translation[1]),
            tform.scale,
            0,
            center=(0, 0),
        )
        img = v2.functional.crop(img, 0, 0, 128, 128)
        img = v2.Resize((112, 112), interpolation=v2.InterpolationMode.BILINEAR, antialias=False)(img)
    else:
        tform = trans.SimilarityTransform()
        tform.estimate(face_kps, arcface_dst)

        img = v2.functional.affine(
            img,
            tform.rotation * 57.2958,
            (tform.translation[0], tform.translation[1]),
            tform.scale,
            0,
            center=(0, 0),
        )
        img = v2.functional.crop(img, 0, 0, 112, 112)

    # Model-specific normalization (matches source)
    if arcface_model_name == "Inswapper128ArcFace":
        cropped_image = img.permute(1, 2, 0).clone()
        if img.dtype == torch.uint8:
            img = img.to(torch.float32)
        img = torch.sub(img, 127.5)
        img = torch.div(img, 127.5)
    elif arcface_model_name == "SimSwapArcFace":
        cropped_image = img.permute(1, 2, 0).clone()
        if img.dtype == torch.uint8:
            img = torch.div(img.to(torch.float32), 255.0)
        img = v2.functional.normalize(
            img, (0.485, 0.456, 0.406), (0.229, 0.224, 0.225), inplace=False
        )
    else:
        cropped_image = img.permute(1, 2, 0).clone()
        if img.dtype == torch.uint8:
            img = img.to(torch.float32)
        img = torch.div(img, 127.5)
        img = torch.sub(img, 1)

    img = torch.unsqueeze(img, 0).contiguous()

    input_name = ort_session.get_inputs()[0].name
    output_names = [o.name for o in ort_session.get_outputs()]
    io_binding = ort_session.io_binding()

    io_binding.bind_input(
        name=input_name,
        device_type=device,
        device_id=0,
        element_type=np.float32,
        shape=tuple(img.size()),
        buffer_ptr=img.data_ptr(),
    )
    for name in output_names:
        io_binding.bind_output(name, device)

    ort_session.run_with_iobinding(io_binding)

    embedding = np.array(io_binding.copy_outputs_to_cpu()).flatten()
    return embedding, cropped_image


def cscs_preprocess_image(
    *,
    img: torch.Tensor,
    face_kps,
    FFHQ_kps,
):
    """
    Source reference:
    - https://github.com/VisoMasterFusion/VisoMaster-Fusion/blob/81eaf3cafe58b3a20a4c4044c060a00d68247291/app/processors/face_swappers.py#L211-L257

    CSCS ArcFace preprocessing (matches FaceSwappers.preprocess_image_cscs):
    - similarity transform from face_kps -> FFHQ_kps
    - affine + crop 512x512
    - resize to 112x112
    - normalize to mean/std (0.5,0.5,0.5)

    Returns
    -------
    input_tensor: torch.Tensor
        Shape (1,3,112,112), float32-like tensor suitable for ORT binding.
    cropped_image: torch.Tensor
        Shape (112,112,3) HWC, cloned.
    """
    tform = trans.SimilarityTransform()
    tform.estimate(face_kps, FFHQ_kps)

    temp = v2.functional.affine(
        img,
        tform.rotation * 57.2958,
        (tform.translation[0], tform.translation[1]),
        tform.scale,
        0,
        center=(0, 0),
    )
    temp = v2.functional.crop(temp, 0, 0, 512, 512)

    image = v2.Resize((112, 112), interpolation=v2.InterpolationMode.BILINEAR, antialias=False)(temp)

    cropped_image = image.permute(1, 2, 0).clone()
    if image.dtype == torch.uint8:
        image = torch.div(image.to(torch.float32), 255.0)

    image = v2.functional.normalize(image, (0.5, 0.5, 0.5), (0.5, 0.5, 0.5), inplace=False)

    return torch.unsqueeze(image, 0).contiguous(), cropped_image


def cscs_recognize_id_adapter(
    ort_session_id,
    *,
    device: str,
    img: torch.Tensor,
    face_kps,
    FFHQ_kps,
):
    """
    Source reference:
    - https://github.com/VisoMasterFusion/VisoMaster-Fusion/blob/81eaf3cafe58b3a20a4c4044c060a00d68247291/app/processors/face_swappers.py#L299-L354

    CSCS ID adapter embedding (matches FaceSwappers.recognize_cscs_id_adapter).

    If face_kps is not None, img is treated as the ORIGINAL image (CHW) and will be preprocessed.
    If face_kps is None, img is assumed to already be preprocessed as (1,3,112,112).

    Returns
    -------
    embedding_id: np.ndarray
        Flattened, L2-normalized embedding.
    """
    if face_kps is not None:
        # Inline dependency on cscs_preprocess_image (still top-level only, no nested helpers)
        img, _ = cscs_preprocess_image(img=img, face_kps=face_kps, FFHQ_kps=FFHQ_kps)

    io_binding = ort_session_id.io_binding()
    io_binding.bind_input(
        name="input",
        device_type=device,
        device_id=0,
        element_type=np.float32,
        shape=tuple(img.size()),
        buffer_ptr=img.data_ptr(),
    )
    io_binding.bind_output(name="output", device_type=device)

    ort_session_id.run_with_iobinding(io_binding)

    output = io_binding.copy_outputs_to_cpu()[0]
    embedding_id = torch.from_numpy(output).to("cpu")
    embedding_id = torch.nn.functional.normalize(embedding_id, dim=-1, p=2)
    return embedding_id.numpy().flatten()


def cscs_recognize(
    ort_session_arcface,
    ort_session_id,
    *,
    device: str,
    img: torch.Tensor,
    face_kps,
    FFHQ_kps,
):
    """
    Source reference:
    - https://github.com/VisoMasterFusion/VisoMaster-Fusion/blob/81eaf3cafe58b3a20a4c4044c060a00d68247291/app/processors/face_swappers.py#L259-L297

    CSCS ArcFace embedding (matches FaceSwappers.recognize_cscs):
    - preprocess with FFHQ landmarks
    - run CSCSArcFace model
    - L2 normalize
    - add ID adapter embedding

    Returns
    -------
    embedding: np.ndarray
        Combined embedding (arcface + id_adapter), flattened.
    cropped_image: torch.Tensor
        Preprocessed cropped face image (112,112,3) HWC.
    """
    # Inline dependency on cscs_preprocess_image (still top-level only, no nested helpers)
    img_pre, cropped_image = cscs_preprocess_image(img=img, face_kps=face_kps, FFHQ_kps=FFHQ_kps)

    io_binding = ort_session_arcface.io_binding()
    io_binding.bind_input(
        name="input",
        device_type=device,
        device_id=0,
        element_type=np.float32,
        shape=tuple(img_pre.size()),
        buffer_ptr=img_pre.data_ptr(),
    )
    io_binding.bind_output(name="output", device_type=device)

    ort_session_arcface.run_with_iobinding(io_binding)

    output = io_binding.copy_outputs_to_cpu()[0]
    embedding = torch.from_numpy(output).to("cpu")
    embedding = torch.nn.functional.normalize(embedding, dim=-1, p=2)
    embedding = embedding.numpy().flatten()

    # Inline dependency on cscs_recognize_id_adapter (still top-level only, no nested helpers)
    embedding_id = cscs_recognize_id_adapter(
        ort_session_id,
        device=device,
        img=img_pre,
        face_kps=None,
        FFHQ_kps=FFHQ_kps,
    )

    embedding = embedding + embedding_id
    return embedding, cropped_image


def recognize_command(
    path_value: str, *, save_faces: int | list[int] = 512, threshold: float = 0.5
) -> int:
    input_path = Path(path_value).expanduser()
    if not input_path.exists():
        print(f"Path not found: {input_path}", file=sys.stderr)
        return 1

    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
    if input_path.is_file() and input_path.suffix.lower() not in image_exts:
        print(f"Unsupported image extension: {input_path.suffix}", file=sys.stderr)
        return 1

    output_dir = input_path / "arcfaces" if input_path.is_dir() else input_path.parent / "arcfaces"
    if output_dir.exists():
        has_existing = any(output_dir.iterdir())
        if has_existing:
            try:
                reply = input(f"Arcfaces output exists at {output_dir}. Reuse existing files? [Y/n]: ")
            except EOFError:
                reply = ""
            reply = reply.strip().lower()
            if reply in ("n", "no"):
                shutil.rmtree(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
            else:
                print(f"Reusing existing arcfaces output: {output_dir}")
                return 0
    else:
        output_dir.mkdir(parents=True)
    input_root = input_path if input_path.is_dir() else input_path.parent

    images: list[Path] = []
    if input_path.is_file():
        images = [input_path]
    else:
        for path in input_path.iterdir():
            if path.is_file() and path.suffix.lower() in image_exts:
                images.append(path)
        images.sort()

    if not images:
        print("No images found.", file=sys.stderr)
        return 1

    models_dir = Path(
        r"S:\Drives\VisoMatrix\Data\Packages\visomaster_fusion_portable\VisoMaster-Fusion\model_assets"
    )
    det_model_path = models_dir / "scrfd_2.5g_bnkps.onnx"
    arcface_model_path = models_dir / "w600k_r50.onnx"

    if not det_model_path.exists():
        print(f"Detector model not found: {det_model_path}", file=sys.stderr)
        return 1
    if not arcface_model_path.exists():
        print(f"ArcFace model not found: {arcface_model_path}", file=sys.stderr)
        return 1

    import cv2
    import onnxruntime as ort
    from tqdm import tqdm

    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    device = "cpu"

    det_session = ort.InferenceSession(str(det_model_path), providers=providers)
    det_input_name = det_session.get_inputs()[0].name
    det_input_size = 640
    det_thresh = 0.5
    nms_thresh = 0.4

    arcface_session = ort.InferenceSession(str(arcface_model_path), providers=providers)
    arcface_dst = np.array(
        [
            (38.2946, 51.6963),
            (73.5318, 51.5014),
            (56.0252, 71.7366),
            (41.5493, 92.3655),
            (70.7299, 92.2041),
        ],
        dtype=np.float32,
    )

    face_items: list[dict[str, object]] = []

    if isinstance(save_faces, int):
        save_sizes = [save_faces]
    else:
        save_sizes = [size for size in save_faces if size > 0]

    for image_path in tqdm(images, desc="ArcFaces", unit="image"):
        output_path = (output_dir / image_path.relative_to(input_root)).with_suffix(".json")
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True, exist_ok=True)

        image_bgr = cv2.imread(str(image_path))
        if image_bgr is None:
            no_faces_path = (output_dir / "faceless" / image_path.relative_to(input_root)).with_suffix(".json")
            if not no_faces_path.parent.exists():
                no_faces_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "image": str(image_path),
                "faces": [],
                "arcface_model": str(arcface_model_path),
                "detector_model": str(det_model_path),
            }
            no_faces_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            continue

        orig_h, orig_w = image_bgr.shape[:2]
        scale_x = orig_w / det_input_size
        scale_y = orig_h / det_input_size

        resized = cv2.resize(image_bgr, (det_input_size, det_input_size), interpolation=cv2.INTER_LINEAR)
        resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        blob = (resized.astype(np.float32) - 127.5) / 128.0
        blob = np.transpose(blob, (2, 0, 1))[None, ...]

        outputs = det_session.run(None, {det_input_name: blob})
        scores_list: list[np.ndarray] = []
        bboxes_list: list[np.ndarray] = []
        kps_list: list[np.ndarray] = []
        for out in outputs:
            if out.ndim == 3 and out.shape[0] == 1:
                out = out[0]
            if out.ndim == 2 and out.shape[1] == 1:
                scores_list.append(out)
            elif out.ndim == 2 and out.shape[1] == 4:
                bboxes_list.append(out)
            elif out.ndim == 2 and out.shape[1] == 10:
                kps_list.append(out)

        order_ns = [
            (det_input_size // 8) * (det_input_size // 8) * 2,
            (det_input_size // 16) * (det_input_size // 16) * 2,
            (det_input_size // 32) * (det_input_size // 32) * 2,
        ]
        ordered_scores: list[np.ndarray] = []
        ordered_bboxes: list[np.ndarray] = []
        ordered_kps: list[np.ndarray] = []
        for n in order_ns:
            for arr in scores_list:
                if arr.shape[0] == n:
                    ordered_scores.append(arr)
                    break
        for n in order_ns:
            for arr in bboxes_list:
                if arr.shape[0] == n:
                    ordered_bboxes.append(arr)
                    break
        for n in order_ns:
            for arr in kps_list:
                if arr.shape[0] == n:
                    ordered_kps.append(arr)
                    break

        all_boxes: list[np.ndarray] = []
        all_scores: list[np.ndarray] = []
        all_kps: list[np.ndarray] = []
        for stride, scores, bbox_pred, kps_pred in zip(
            (8, 16, 32), ordered_scores, ordered_bboxes, ordered_kps
        ):
            fm_h = det_input_size // stride
            fm_w = det_input_size // stride
            xs = np.arange(fm_w, dtype=np.float32)
            ys = np.arange(fm_h, dtype=np.float32)
            xv, yv = np.meshgrid(xs, ys)
            centers = np.stack([(xv + 0.5) * stride, (yv + 0.5) * stride], axis=-1).reshape(-1, 2)
            centers = np.repeat(centers, 2, axis=0)

            scores = scores.reshape(-1)
            keep_mask = scores >= det_thresh
            if not np.any(keep_mask):
                continue

            centers_sel = centers[keep_mask]
            bbox_sel = bbox_pred[keep_mask]
            x1 = centers_sel[:, 0] - bbox_sel[:, 0] * stride
            y1 = centers_sel[:, 1] - bbox_sel[:, 1] * stride
            x2 = centers_sel[:, 0] + bbox_sel[:, 2] * stride
            y2 = centers_sel[:, 1] + bbox_sel[:, 3] * stride
            boxes = np.stack([x1, y1, x2, y2], axis=1)

            kps_sel = kps_pred[keep_mask].reshape(-1, 5, 2)
            kps_sel[:, :, 0] = centers_sel[:, 0:1] + kps_sel[:, :, 0] * stride
            kps_sel[:, :, 1] = centers_sel[:, 1:1 + 1] + kps_sel[:, :, 1] * stride

            boxes[:, [0, 2]] *= scale_x
            boxes[:, [1, 3]] *= scale_y
            kps_sel[:, :, 0] *= scale_x
            kps_sel[:, :, 1] *= scale_y

            all_boxes.append(boxes)
            all_scores.append(scores[keep_mask])
            all_kps.append(kps_sel)

        if not all_boxes:
            no_faces_path = (output_dir / "faceless" / image_path.relative_to(input_root)).with_suffix(".json")
            if not no_faces_path.parent.exists():
                no_faces_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "image": str(image_path),
                "faces": [],
                "arcface_model": str(arcface_model_path),
                "detector_model": str(det_model_path),
            }
            no_faces_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            continue

        boxes = np.concatenate(all_boxes, axis=0)
        scores = np.concatenate(all_scores, axis=0)
        kps_all = np.concatenate(all_kps, axis=0)

        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        areas = (x2 - x1 + 1.0) * (y2 - y1 + 1.0)
        order = scores.argsort()[::-1]
        keep: list[int] = []
        while order.size > 0:
            i = int(order[0])
            keep.append(i)
            if order.size == 1:
                break
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            w = np.maximum(0.0, xx2 - xx1 + 1.0)
            h = np.maximum(0.0, yy2 - yy1 + 1.0)
            inter = w * h
            iou = inter / (areas[i] + areas[order[1:]] - inter)
            order = order[1:][iou <= nms_thresh]

        image_rgb_full = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        torch_img = torch.from_numpy(image_rgb_full).permute(2, 0, 1).contiguous()

        faces = []
        for face_index, i in enumerate(keep):
            face_kps = kps_all[i].astype(np.float32)
            embedding, cropped_image = arcface_recognize(
                arcface_session,
                arcface_model_name="Inswapper128ArcFace",
                device=device,
                img=torch_img,
                face_kps=face_kps,
                similarity_type="Opal",
                arcface_dst=arcface_dst,
            )
            bbox = boxes[i]
            score = float(scores[i])

            pad_ratio = 0.25
            x1 = float(bbox[0])
            y1 = float(bbox[1])
            x2 = float(bbox[2])
            y2 = float(bbox[3])
            w = max(1.0, x2 - x1)
            h = max(1.0, y2 - y1)
            size = max(w, h) * (1.0 + 2.0 * pad_ratio)
            cx = x1 + w * 0.5
            cy = y1 + h * 0.5
            x1p = int(max(0, np.floor(cx - size * 0.5)))
            y1p = int(max(0, np.floor(cy - size * 0.5)))
            x2p = int(min(orig_w, np.ceil(cx + size * 0.5)))
            y2p = int(min(orig_h, np.ceil(cy + size * 0.5)))
            if x2p > x1p and y2p > y1p:
                crop_bgr = image_bgr[y1p:y2p, x1p:x2p]
            else:
                crop_bgr = cropped_image.detach().cpu().numpy()
                if crop_bgr.dtype != np.uint8:
                    if crop_bgr.max() <= 1.0:
                        crop_bgr = crop_bgr * 255.0
                    crop_bgr = np.clip(crop_bgr, 0, 255).astype(np.uint8)
                if crop_bgr.ndim == 3 and crop_bgr.shape[2] == 3:
                    crop_bgr = cv2.cvtColor(crop_bgr, cv2.COLOR_RGB2BGR)

            crop_base = crop_bgr
            crop_entries: list[dict[str, object]] = []
            for save_size in save_sizes:
                output_image_path = output_path.with_name(
                    f"{output_path.stem}__face{face_index}__{save_size}{image_path.suffix}"
                )
                crop_out = crop_base
                crop_h, crop_w = crop_base.shape[:2]
                if crop_h > 0 and crop_w > 0:
                    interp = cv2.INTER_AREA if max(crop_h, crop_w) > save_size else cv2.INTER_LINEAR
                    crop_out = cv2.resize(crop_base, (save_size, save_size), interpolation=interp)
                cv2.imwrite(str(output_image_path), crop_out)
                crop_entries.append({"size": save_size, "path": str(output_image_path)})

            faces.append(
                {
                    "index": face_index,
                    "bbox": [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])],
                    "score": score,
                    "kps": face_kps.tolist(),
                    "embedding": embedding.astype(float).tolist(),
                    "crop": str(crop_entries[0]["path"]) if crop_entries else "",
                    "crops": crop_entries,
                }
            )

        for face in faces:
            face_items.append(
                {
                    "embedding": np.asarray(face["embedding"], dtype=np.float32),
                    "payload": {
                        "image": str(image_path),
                        "face": {
                            "index": face["index"],
                            "bbox": face["bbox"],
                            "score": face["score"],
                            "kps": face["kps"],
                            "embedding": face["embedding"],
                        },
                        "arcface_model": str(arcface_model_path),
                        "detector_model": str(det_model_path),
                    },
                    "json_path": output_path.with_name(f"{output_path.stem}__face{face['index']}.json"),
                    "crop_paths": [Path(entry["path"]) for entry in face["crops"]],
                    "crop_sizes": [entry["size"] for entry in face["crops"]],
                }
            )

    if face_items:
        clusters: list[dict[str, object]] = []
        for item in face_items:
            emb = item["embedding"]
            norm = float(np.linalg.norm(emb))
            emb_norm = emb / norm if norm > 0.0 else emb

            best_idx = -1
            best_sim = -1.0
            for idx, cluster in enumerate(clusters):
                rep = cluster["rep"]
                sim = float(np.dot(emb_norm, rep))
                if sim > best_sim:
                    best_sim = sim
                    best_idx = idx

            if best_idx >= 0 and best_sim >= threshold:
                cluster = clusters[best_idx]
                cluster["sum"] = cluster["sum"] + emb_norm
                cluster["count"] = cluster["count"] + 1
                cluster["rep"] = cluster["sum"] / float(np.linalg.norm(cluster["sum"]))
                cluster["items"].append(item)
            else:
                clusters.append(
                    {
                        "sum": emb_norm.copy(),
                        "count": 1,
                        "rep": emb_norm.copy(),
                        "items": [item],
                    }
                )

        for idx, cluster in enumerate(clusters):
            cluster_dir = output_dir / f"identity_{idx:03d}"
            if not cluster_dir.exists():
                cluster_dir.mkdir(parents=True, exist_ok=True)
            for item in cluster["items"]:
                json_dest = cluster_dir / item["json_path"].name
                crop_paths = item["crop_paths"]
                crop_sizes = item["crop_sizes"]
                crop_destinations: list[str] = []
                for crop_path in crop_paths:
                    crop_dest = cluster_dir / crop_path.name
                    if crop_path.exists():
                        crop_path.replace(crop_dest)
                    crop_destinations.append(str(crop_dest))
                payload = item["payload"]
                payload["identity"] = cluster_dir.name
                if crop_destinations:
                    payload["face"]["crop"] = crop_destinations[0]
                    payload["face"]["crops"] = [
                        {"size": crop_sizes[index], "path": crop_destinations[index]}
                        for index in range(len(crop_destinations))
                    ]
                json_dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Wrote {len(images)} file(s) to {output_dir}")
    return 0


def top_identity(path_value: str, *, count: int = 1) -> int:
    base_path = Path(path_value).expanduser()
    if count < 1:
        print("Count must be at least 1.", file=sys.stderr)
        return 1
    if base_path.is_dir() and base_path.name == "arcfaces":
        output_dir = base_path
    else:
        output_dir = base_path / "arcfaces" if base_path.is_dir() else base_path.parent / "arcfaces"

    if not output_dir.exists():
        print(f"Arcfaces folder not found: {output_dir}", file=sys.stderr)
        return 1

    identity_dirs = [
        path for path in output_dir.iterdir() if path.is_dir() and path.name.startswith("identity_")
    ]
    if not identity_dirs:
        print("No identity folders found.", file=sys.stderr)
        return 1

    if base_path.is_dir():
        source_dir = base_path.parent if base_path.name == "arcfaces" else base_path
    else:
        source_dir = base_path.parent
    ranked_identities: list[tuple[int, str, Path]] = []
    for identity_dir in sorted(identity_dirs):
        face_count = sum(
            1 for path in identity_dir.iterdir() if path.is_file() and path.suffix.lower() == ".json"
        )
        ranked_identities.append((face_count, identity_dir.name, identity_dir))

    ranked_identities.sort(key=lambda item: (-item[0], item[1]))
    selected = ranked_identities[: min(count, len(ranked_identities))]
    if not selected:
        print("No identity detections found.", file=sys.stderr)
        return 1

    destinations: list[Path] = []
    for _, _, identity_dir in selected:
        destination = source_dir / identity_dir.name
        if destination.exists():
            print(f"Destination already exists: {destination}", file=sys.stderr)
            return 1
        destinations.append(destination)

    for (_, _, identity_dir), destination in zip(selected, destinations):
        shutil.move(str(identity_dir), str(destination))
        print(str(destination))
    return 0
