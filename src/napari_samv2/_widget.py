# Imports
import os
import numpy as np
import napari
import requests
from pipelines.samv2.Samv2_pipeline_handler import SamV2_pipeline
from qtpy import uic
from qtpy.QtWidgets import (
    QComboBox,
    QFileDialog,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QWidget,
)
from pathlib import Path


# Main Plugin class that is connected from outside at napari plugin entry point
class SAMV2_min(QWidget):
    def __init__(self, napari_viewer):
        # Initializing
        super().__init__()
        self.viewer = napari_viewer

        # Load the UI file - Main window
        script_dir = os.path.dirname(__file__)
        ui_file_name = "SAM_V2.ui"
        abs_file_path = os.path.join(
            script_dir, "..", "UI_files", ui_file_name
        )
        uic.loadUi(abs_file_path, self)

        # Get required children for functionality addition
        self.image_layers_combo = self.findChild(
            QComboBox, "Image_layer_combo"
        )
        self.interdir_lineedt = self.findChild(QLineEdit, "inter_lineedt")
        self.interdir_browse_btn = self.findChild(
            QPushButton, "inter_browse_btn"
        )
        self.output_layers_combo = self.findChild(
            QComboBox, "output_layer_combo"
        )
        self.model_cbbox = self.findChild(QComboBox, "model_cbbox")

        self.initialize_btn = self.findChild(QPushButton, "Initialize_btn")
        self.video_propagation_progressBar = self.findChild(
            QProgressBar, "Propagation_progress"
        )
        self.video_propagate_btn = self.findChild(QPushButton, "Propagate_btn")
        self.reset_btn = self.findChild(QPushButton, "reset_btn")
        #self.reset_and_prop_btn = self.findChild(QPushButton, "reset_and_prop")

        # Populate combo box - call
        self.populate_combo_box(self.image_layers_combo, "image")
        self.populate_combo_box(self.output_layers_combo, "label")
        self.populate_model_combo()


        # Connect events to functions
        self.viewer.layers.events.inserted.connect(self.layer_changed)
        self.viewer.layers.events.removed.connect(self.layer_changed)
        self.viewer.layers.events.changed.connect(self.layer_changed)
        self.viewer.mouse_drag_callbacks.append(self.on_mouse_click)

        # Connect button to functions
        self.interdir_browse_btn.clicked.connect(self.choose_inter_frame_dir)
        self.initialize_btn.clicked.connect(self.initialize_pipeline)
        self.video_propagate_btn.clicked.connect(self.video_propagate)
        self.reset_btn.clicked.connect(self.reset_everything)
        #self.reset_and_prop_btn.clicked.connect(self.reset_and_propagate)

        # Key board shortcut
        @napari_viewer.bind_key('a')
        def add_positive_point(napari_viewer):
            """Add a positive point at the current cursor position using 'a' key"""
            if self.pipeline_object is None:
                return
            position = self.viewer.cursor.position
            if position is None:
                return
            point = [int(position[0]), int(position[1]), int(position[2])]
            layer_name = self.output_layers_combo.currentText()
            if layer_name not in self.viewer.layers:
                return
            layer = self.viewer.layers[layer_name]
            active_label = layer.selected_label
            self.pipeline_object.add_point(point, active_label, neg_or_pos=1)
            # Update Positive Points layer
            if "Positive Points" in self.viewer.layers:
                pos_layer = self.viewer.layers["Positive Points"]
                if pos_layer.data.size == 0:
                    pos_layer.data = np.array([point])
                else:
                    pos_layer.data = np.concatenate([pos_layer.data, [point]], axis=0)

        @napari_viewer.bind_key('n')
        def add_negative_point(napari_viewer):
            """Add a negative point at the current cursor position using 'n' key"""
            if self.pipeline_object is None:
                return
            position = self.viewer.cursor.position
            if position is None:
                return
            point = [int(position[0]), int(position[1]), int(position[2])]
            layer_name = self.output_layers_combo.currentText()
            if layer_name not in self.viewer.layers:
                return
            layer = self.viewer.layers[layer_name]
            active_label = layer.selected_label
            self.pipeline_object.add_point(point, active_label, neg_or_pos=0)
            # Update Negative Points layer
            if "Negative Points" in self.viewer.layers:
                neg_layer = self.viewer.layers["Negative Points"]
                if neg_layer.data.size == 0:
                    neg_layer.data = np.array([point])
                else:
                    neg_layer.data = np.concatenate([neg_layer.data, [point]], axis=0)

    # Function to populate combo boxes based on layers
    def populate_combo_box(self, combobx, layer_type="image"):
        # Clear the combo box first
        combobx.clear()
        if layer_type == "image":
            # Get all existing image layers from the napari viewer
            layers = [
                layer.name
                for layer in self.viewer.layers
                if isinstance(layer, napari.layers.Image)
            ]
        elif layer_type == "label":
            # Get all existing label layers from the napari viewer
            layers = [
                layer.name
                for layer in self.viewer.layers
                if isinstance(layer, napari.layers.Labels)
            ]
        else:
            raise ValueError(
                "Invalid layer_type. Expected 'image' or 'label'."
            )

        combobx.addItems(layers)

    # Function to handle combobox state change
    def layer_changed(self):
        # Populate combo box - call
        self.populate_combo_box(self.image_layers_combo, "image")
        self.populate_combo_box(self.output_layers_combo, "label")

    # add models in cbbox
    def populate_model_combo(self):
        self.model_cbbox.clear()
        self.model_cbbox.addItems(
            [
                "sam2.1_hiera_large",
                "sam2.1_hiera_small",
                "sam2.1_hiera_tiny",
                "sam2.1_hiera_base_plus",

            ]
        )

    # Choose inter frame dir
    def choose_inter_frame_dir(self):
        dname = QFileDialog.getExistingDirectory()
        print(dname)
        self.interdir_lineedt.setText(str(dname))

    # Initialize pipeline
    BASE_URL = "https://dl.fbaipublicfiles.com/segment_anything_2/092824/"
    CHECKPOINTS = {
        "sam2.1_hiera_tiny": "sam2.1_hiera_tiny.pt",
        "sam2.1_hiera_small": "sam2.1_hiera_small.pt",
        "sam2.1_hiera_base_plus": "sam2.1_hiera_base_plus.pt",
        "sam2.1_hiera_large": "sam2.1_hiera_large.pt",
    }

    def initialize_pipeline(self):
        script_dir = os.path.dirname(__file__)
        model_map = {
            "sam2.1_hiera_large": ("configs/sam2.1/sam2.1_hiera_l.yaml", "sam2.1_hiera_large.pt"),
            "sam2.1_hiera_small": ("configs/sam2.1/sam2.1_hiera_s.yaml", "sam2.1_hiera_small.pt"),
            "sam2.1_hiera_tiny": ("configs/sam2.1/sam2.1_hiera_t.yaml", "sam2.1_hiera_tiny.pt"),
            "sam2.1_hiera_base_plus": ("configs/sam2.1/sam2.1_hiera_b+.yaml", "sam2.1_hiera_base_plus.pt"),
        }
        selected_model = self.model_cbbox.currentText()
        if selected_model in model_map:
            model_cfg, checkpoint_name = model_map[selected_model]
            model_path_parent_folder = Path(self.interdir_lineedt.text()) / Path("models")
            model_path_parent_folder.mkdir(parents=True, exist_ok=True)
            checkpoint_path = os.path.join(
                str(model_path_parent_folder), checkpoint_name
            )
            """
            checkpoint_path = os.path.join(
                script_dir, "..", "model", checkpoint_name
            )
            """
            if not os.path.exists(checkpoint_path):
                print(f"Checkpoint {checkpoint_name} not found. Downloading...")
                self.download_checkpoint(checkpoint_name, checkpoint_path)
            self.pipeline_object = SamV2_pipeline(
                self.viewer, self, checkpoint_path, model_cfg
            )

            # Create two points layers (if they don't already exist)
            if "Positive Points" not in self.viewer.layers:
                self.viewer.add_points(name="Positive Points", data=[], ndim=3)
            if "Negative Points" not in self.viewer.layers:
                self.viewer.add_points(name="Negative Points", data=[], ndim=3)

            self.viewer.layers.selection = {self.viewer.layers[self.output_layers_combo.currentText()]}
        else:
            print("Model not recognized.")

    def download_checkpoint(self, checkpoint_name, checkpoint_path):
        url = self.BASE_URL + checkpoint_name

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Check if the download was successful

            with open(checkpoint_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            print(f"{checkpoint_name} downloaded successfully.")

        except requests.exceptions.RequestException as e:
            print(
                f"Failed to download {checkpoint_name} from {url}. Error: {e}"
            )

    def on_mouse_click(self, layer, event):
        if event.button == 3:  # Middle click
            point = [int(event.position[0]), int(event.position[1]), int(event.position[2])]
            layer_name = self.output_layers_combo.currentText()
            if layer_name not in self.viewer.layers:
                return
            layer = self.viewer.layers[layer_name]
            active_label = layer.selected_label
            if "Control" in event.modifiers:
                # Negative point
                self.pipeline_object.add_point(point, active_label, neg_or_pos=0)
                if "Negative Points" in self.viewer.layers:
                    neg_layer = self.viewer.layers["Negative Points"]
                    if neg_layer.data.size == 0:
                        neg_layer.data = np.array([point])
                    else:
                        neg_layer.data = np.concatenate([neg_layer.data, [point]], axis=0)
            else:
                # Positive point
                self.pipeline_object.add_point(point, active_label, neg_or_pos=1)
                if "Positive Points" in self.viewer.layers:
                    pos_layer = self.viewer.layers["Positive Points"]
                    if pos_layer.data.size == 0:
                        pos_layer.data = np.array([point])
                    else:
                        pos_layer.data = np.concatenate([pos_layer.data, [point]], axis=0)

    def video_propagate(self):
        self.pipeline_object.video_propagate()

    def reset_everything(self):
        self.pipeline_object.reset()

    def reset_and_propagate(self):
        self.pipeline_object.reset_and_video_propagate()