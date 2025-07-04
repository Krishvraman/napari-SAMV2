import os
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from qtpy.QtWidgets import QWidget
from sam2.build_sam import build_sam2_video_predictor


# Sam V2 pipeline class
class SamV2_pipeline(QWidget):
    def __init__(
            self,
            napari_viewer,
            main_window_object,
            checkpoint_path,
            model_cfg_name,
    ):
        super().__init__()
        self.viewer = napari_viewer
        self.mwo = main_window_object
        self.source_frame_dir = (
            None  # Will be set inside process volume function
        )

        # torch autocast - following samv2 recommended execution code
        torch.autocast(device_type="cuda", dtype=torch.bfloat16).__enter__()
        if torch.cuda.get_device_properties(0).major >= 8:
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

        DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        sam2_checkpoint = checkpoint_path
        model_cfg = model_cfg_name

        self.predictor = build_sam2_video_predictor(model_cfg, sam2_checkpoint)

        self.preprocess_volume()

        self.inference_state = self.predictor.init_state(
            video_path=self.source_frame_dir.as_posix()
        )

        self.prompts = {}

    def preprocess_volume(self):
        layer_name = self.mwo.image_layers_combo.currentText()
        layer = self.viewer.layers[layer_name]
        volume = layer.data

        # Create a source frame directory
        self.source_frame_dir = Path(self.mwo.interdir_lineedt.text()) / Path(layer_name)
        print("Creating the frame dir ", self.source_frame_dir)
        self.source_frame_dir.mkdir(parents=True, exist_ok=True)

        if volume.ndim == 2:
            # It's a single 2D image
            slice_path = os.path.join(self.source_frame_dir, "0000.jpeg")
            if not os.path.exists(slice_path):
                slice = volume

                if slice.dtype != np.uint8:
                    print(f"Converting 2D image to 8-bit from {slice.dtype}")
                    slice = self._convert_to_8bit(slice)

                slice_array = Image.fromarray(slice)
                slice_array.save(slice_path)

            print("Single Frame Generated")

        elif volume.ndim == 3:
            # It's a volume
            for i in range(volume.shape[0]):
                slice_path = os.path.join(self.source_frame_dir, f"{i:04d}.jpeg")
                if os.path.exists(slice_path):
                    continue

                slice = volume[i, :, :]

                if slice.dtype != np.uint8:
                    print(f"Converting slice {i} to 8-bit from {slice.dtype}")
                    slice = self._convert_to_8bit(slice)

                slice_array = Image.fromarray(slice)
                slice_array.save(slice_path)

            print("Frames Generated")
        else:
            print(f"Unsupported number of dimensions: {volume.ndim}")

    # Helper function to convert slices to 8-bit
    def _convert_to_8bit(self, slice):
        if slice.dtype == np.uint16:
            type_min, type_max = 0, 65535
        elif slice.dtype == np.int16:
            type_min, type_max = -32768, 32767
        elif slice.dtype in (np.float32, np.float64):
            type_min, type_max = 0.0, 1.0
            if slice.max() > 1.0:
                type_max = 255.0 if slice.max() < 256.0 else slice.max()
        else:
            type_min, type_max = slice.min(), slice.max()

        if type_min == type_max:
            slice_normalized = np.zeros(slice.shape, dtype=np.uint8)
        else:
            slice_normalized = np.clip(
                ((slice.astype(float) - type_min) / (type_max - type_min) * 255.0),
                0, 255
            ).astype(np.uint8)

        return slice_normalized

    def add_point(self, point_array, label_id, neg_or_pos=1):
        ann_frame_idx = point_array[0]
        ann_obj_id = label_id
        new_point = [point_array[2], point_array[1]]
        new_label = neg_or_pos
        check_if_our_z_is_new = True
        check_if_our_annotation_is_new = True
        # print(ann_obj_id)

        # Check if in dict else add it
        if ann_obj_id in self.prompts:
            all_list = []
            for existing_list in self.prompts[ann_obj_id]:
                if existing_list[0] == ann_frame_idx:
                    points = existing_list[1]
                    labels = list(existing_list[2])
                    points = np.append(points, [new_point], axis=0)
                    labels.append(new_label)
                    new_list = [
                        ann_frame_idx,
                        points,
                        np.array(labels, np.int32),
                    ]
                    all_list.append(new_list)
                    check_if_our_z_is_new = False
                else:
                    all_list.append(existing_list)

            self.prompts[ann_obj_id] = all_list
            check_if_our_annotation_is_new = False

        else:
            points = np.array(
                [[point_array[2], point_array[1]]], dtype=np.float32
            )
            labels = np.array([neg_or_pos], np.int32)
            self.prompts[ann_obj_id] = [[ann_frame_idx, points, labels]]

        if check_if_our_z_is_new and not (check_if_our_annotation_is_new):
            points = np.array(
                [[point_array[2], point_array[1]]], dtype=np.float32
            )
            labels = np.array([neg_or_pos], np.int32)
            existing_val = self.prompts[ann_obj_id]
            existing_val.append(
                [ann_frame_idx, points, labels]
            )
            self.prompts[ann_obj_id] = existing_val

            # print(labels,points,ann_frame_idx)

        layer_name = self.mwo.output_layers_combo.currentText()
        layer = self.viewer.layers[layer_name]
        label_layer_data = layer.data

        _, out_obj_ids, out_mask_logits = self.predictor.add_new_points_or_box(
            inference_state=self.inference_state,
            frame_idx=ann_frame_idx,
            obj_id=ann_obj_id,
            points=points,
            labels=labels,
        )
        mask_for_this_frame = np.zeros(
            (label_layer_data.shape[1], label_layer_data.shape[2]),
            dtype=np.int32,
        )
        for i, out_obj_id in enumerate(out_obj_ids):
            out_mask = (out_mask_logits[i] > 0.0).cpu().numpy()
            # print(out_mask.shape)
            mask_for_this_frame[out_mask[0] == True] = out_obj_id

        label_layer_data[ann_frame_idx, :, :] = mask_for_this_frame
        layer.data = label_layer_data

    def video_propagate(self):
        # run propagation throughout the video and collect the results in a dict
        layer_name = self.mwo.output_layers_combo.currentText()
        layer = self.viewer.layers[layer_name]
        label_layer_data = layer.data
        label_layer_data_2 = label_layer_data.copy()
        firsttime = True

        print("Executing forward")
        for (
                out_frame_idx,
                out_obj_ids,
                out_mask_logits,
        ) in self.predictor.propagate_in_video(
            self.inference_state, start_frame_idx=0
        ):
            mask_for_this_frame = np.zeros(
                (label_layer_data.shape[1], label_layer_data.shape[2]),
                dtype=np.int32,
            )
            for i, out_obj_id in enumerate(out_obj_ids):
                out_mask = (out_mask_logits[i] > 0.0).cpu().numpy()
                # print(out_mask.shape)
                mask_for_this_frame[out_mask[0] == True] = out_obj_id

            label_layer_data[out_frame_idx, :, :] = mask_for_this_frame
            progress = int((out_frame_idx * 50) / label_layer_data.shape[0])
            self.mwo.video_propagation_progressBar.setValue(progress)

        print("Executing reverse")
        for (
                out_frame_idx,
                out_obj_ids,
                out_mask_logits,
        ) in self.predictor.propagate_in_video(
            self.inference_state,
            start_frame_idx=label_layer_data.shape[0] - 1,
            reverse=True,
        ):
            mask_for_this_frame = np.zeros(
                (label_layer_data.shape[1], label_layer_data.shape[2]),
                dtype=np.int32,
            )
            for i, out_obj_id in enumerate(out_obj_ids):
                out_mask = (out_mask_logits[i] > 0.0).cpu().numpy()
                print(out_mask.shape)
                mask_for_this_frame[out_mask[0] == True] = out_obj_id

            label_layer_data_2[out_frame_idx, :, :] = mask_for_this_frame

            if firsttime:
                final_progress_here = int(
                    (out_frame_idx * 50) / label_layer_data.shape[0]
                )
                firsttime = False

            progress = int((out_frame_idx * 50) / label_layer_data.shape[0])
            progress = abs(final_progress_here - progress) + 50
            self.mwo.video_propagation_progressBar.setValue(progress)

        layer.data = np.maximum(label_layer_data, label_layer_data_2)
        # self.mwo.video_propagation_progressBar.setValue(progress)
        self.mwo.video_propagation_progressBar.setValue(100)

    def reset(self):
        self.predictor.reset_state(self.inference_state)
        layer_name = self.mwo.output_layers_combo.currentText()
        layer = self.viewer.layers[layer_name]
        label_layer_data = layer.data
        zero_mask = np.zeros(label_layer_data.shape, dtype=np.int32)
        layer.data = zero_mask

    def reset_and_video_propagate(self):
        #Clear existing prompts
        self.prompts = {}

        #Read points from Positive Points layer
        if "Positive Points" in self.viewer.layers:
            pos_layer = self.viewer.layers["Positive Points"]
            for point in pos_layer.data:
                z, y, x = map(int, point)
                layer_name = self.mwo.output_layers_combo.currentText()
                label_layer = self.viewer.layers[layer_name]
                active_label = label_layer.selected_label
                self.add_point([z, y, x], active_label, neg_or_pos=1)

        #Read points from Negative Points layer
        if "Negative Points" in self.viewer.layers:
            neg_layer = self.viewer.layers["Negative Points"]
            for point in neg_layer.data:
                z, y, x = map(int, point)
                layer_name = self.mwo.output_layers_combo.currentText()
                label_layer = self.viewer.layers[layer_name]
                active_label = label_layer.selected_label
                self.add_point([z, y, x], active_label, neg_or_pos=0)

        # Step 4: Now propagate after adding points
        layer_name = self.mwo.output_layers_combo.currentText()
        layer = self.viewer.layers[layer_name]
        label_layer_data = layer.data
        label_layer_data_2 = label_layer_data.copy()
        firsttime = True

        print("Executing forward")
        for (
                out_frame_idx,
                out_obj_ids,
                out_mask_logits,
        ) in self.predictor.propagate_in_video(
            self.inference_state, start_frame_idx=0
        ):
            mask_for_this_frame = np.zeros(
                (label_layer_data.shape[1], label_layer_data.shape[2]),
                dtype=np.int32,
            )
            for i, out_obj_id in enumerate(out_obj_ids):
                out_mask = (out_mask_logits[i] > 0.0).cpu().numpy()
                mask_for_this_frame[out_mask[0] == True] = out_obj_id

            label_layer_data[out_frame_idx, :, :] = mask_for_this_frame
            progress = int((out_frame_idx * 50) / label_layer_data.shape[0])
            self.mwo.video_propagation_progressBar.setValue(progress)

        print("Executing reverse")
        for (
                out_frame_idx,
                out_obj_ids,
                out_mask_logits,
        ) in self.predictor.propagate_in_video(
            self.inference_state,
            start_frame_idx=label_layer_data.shape[0] - 1,
            reverse=True,
        ):
            mask_for_this_frame = np.zeros(
                (label_layer_data.shape[1], label_layer_data.shape[2]),
                dtype=np.int32,
            )
            for i, out_obj_id in enumerate(out_obj_ids):
                out_mask = (out_mask_logits[i] > 0.0).cpu().numpy()
                mask_for_this_frame[out_mask[0] == True] = out_obj_id

            label_layer_data_2[out_frame_idx, :, :] = mask_for_this_frame

            if firsttime:
                final_progress_here = int(
                    (out_frame_idx * 50) / label_layer_data.shape[0]
                )
                firsttime = False

            progress = int((out_frame_idx * 50) / label_layer_data.shape[0])
            progress = abs(final_progress_here - progress) + 50
            self.mwo.video_propagation_progressBar.setValue(progress)

        # Final step: Combine forward and reverse
        layer.data = np.maximum(label_layer_data, label_layer_data_2)
        self.mwo.video_propagation_progressBar.setValue(100)