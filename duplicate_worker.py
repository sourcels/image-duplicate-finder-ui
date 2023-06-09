# -*- coding: utf-8 -*-
import cv2, os

from pathlib import Path
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QWidget, QMessageBox


class DuplicateWorker:
    def __init__(self, parent: QWidget = None):
        self.parent = parent
        self.duplicate_count = 0
        self.moved_duplicate_count = 0

    def calculate_mean(self, pixels_list):
        mean = 0
        total_pixels = len(pixels_list)
        for i in range(total_pixels):
            mean += pixels_list[i] / total_pixels
        return mean

    def grab_pixels(self, squeezed_frame):
        pixels_list = []
        for x in range(0, squeezed_frame.shape[1], 1):
            for y in range(0, squeezed_frame.shape[0], 1):
                pixel_color = squeezed_frame[x, y]
                pixels_list.append(pixel_color)
        return pixels_list

    def make_bits_list(self, mean, pixels_list):
        bits_list = []
        for i in range(len(pixels_list)):
            if pixels_list[i] >= mean:
                bits_list.append(255)
            else:
                bits_list.append(0)
        return bits_list

    def hashify(self, squeezed_frame, bits_list):
        bit_index = 0
        hashed_frame = squeezed_frame
        for x in range(0, squeezed_frame.shape[1], 1):
            for y in range(0, squeezed_frame.shape[0], 1):
                hashed_frame[x, y] = bits_list[bit_index]
                bit_index += 1
        return hashed_frame

    def generate_hash(self, frame, hash_size):
        frame_squeezed = cv2.resize(frame, (hash_size, hash_size))
        frame_squeezed = cv2.cvtColor(frame_squeezed, cv2.COLOR_BGR2GRAY)
        pixels_list = self.grab_pixels(frame_squeezed)
        mean_color = self.calculate_mean(pixels_list)
        bits_list = self.make_bits_list(mean_color, pixels_list)
        hashed_frame = self.hashify(frame_squeezed, bits_list)
        hashed_frame = cv2.cvtColor(hashed_frame, cv2.COLOR_GRAY2BGR)
        return bits_list, hashed_frame

    def clean_folder(self, files, source_folder_path: str, duplicate_folder_path: str, threshold: int, isAsking: bool, hash_size: int = 16):
        if files == []:
            raise FileNotFoundError
        list_length = len(files)
        frame = None
        hashed_frame = None
        bits_list = []
        self.parent.logger.info(f"Searching duplicates in {source_folder_path}, hash_size: {hash_size}, threshold: {threshold}")
        self.parent.log_label.setText(self.parent.logger.handlers[0].widget.toPlainText())
        i = 0
        k = 1
        while i < len(files):
            sum_diff = 0
            if files[i] is not None:
                frame = cv2.imread(files[i], cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
                bits_list, hashed_frame = self.generate_hash(frame, hash_size)

            while k < len(files):
                if (i != k) and (files[k] is not None):
                    new_frame = cv2.imread(files[k], cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
                    new_bits_list, hashed_second_frame = self.generate_hash(new_frame, hash_size)

                    for j in range(len(bits_list)):
                        if bits_list[j] != new_bits_list[j]:
                            sum_diff += 1

                    self.parent.logger.info(f"{files[i]} -> {files[k]} sum_diff = {sum_diff}")
                    self.parent.log_label.setText(self.parent.logger.handlers[0].widget.toPlainText())

                    if sum_diff <= hash_size * hash_size * threshold / 100:
                        self.duplicate_count += 1

                    im_h = cv2.hconcat([cv2.resize(frame, (200, 200)), cv2.resize(new_frame, (200, 200))])
                    im_h2 = cv2.hconcat([cv2.resize(hashed_frame, (200, 200)), cv2.resize(hashed_second_frame, (200, 200))])
                    im_v = cv2.vconcat([im_h, im_h2])
                    cv2.putText(im_v, f"SIMILAR: {self.duplicate_count}", (5, 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, lineType=cv2.LINE_AA)
                    img = cv2.cvtColor(im_v, cv2.COLOR_BGR2RGB)
                    h, w, ch = img.shape
                    bytes_per_line = ch * w
                    q_img = QPixmap(QImage(img.data, w, h, bytes_per_line, QImage.Format_RGB888))
                    self.parent.image_label.setPixmap(q_img)
                    if sum_diff <= hash_size * hash_size * threshold / 100:
                        if isAsking:
                            reply = QMessageBox.question(self.parent, "Found difference", f"Found {k} element ({files[k]}) of {list_length}\nMove it to {self.parent.output_folder_label.toolTip()}?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                        if not isAsking or reply == QMessageBox.Yes:
                            if os.path.exists(os.path.join(duplicate_folder_path, files[k].split("\\")[-1])):
                                os.remove(os.path.join(duplicate_folder_path, files[k].split("\\")[-1]))
                                Path(files[k]).rename(os.path.join(duplicate_folder_path, files[k].split("\\")[-1]))
                                self.parent.logger.warning(f"{files[k]} already exists in {source_folder_path}, rewriting")
                                self.parent.log_label.setText(self.parent.logger.handlers[0].widget.toPlainText())
                            else:
                                Path(files[k]).rename(os.path.join(duplicate_folder_path, files[k].split("\\")[-1]))
                            self.parent.logger.info(f"Moved {k} element ({files[k]}) of {list_length}")
                            self.parent.log_label.setText(self.parent.logger.handlers[0].widget.toPlainText())
                            del files[k]
                            self.moved_duplicate_count += 1
                        else:
                            self.parent.logger.info(f"Ignored {k} element ({files[k]}) of {list_length}")
                            self.parent.log_label.setText(self.parent.logger.handlers[0].widget.toPlainText())
                            del files[k]
                            k += 1
                    else:
                        k += 1
                    cv2.waitKey(1)
                    sum_diff = 0
            i += 1
            k = i + 1
        self.parent.logger.info(f"Done! Duplicates count: {self.duplicate_count}, Moved duplicates: {self.moved_duplicate_count}")
        self.parent.log_label.setText(self.parent.logger.handlers[0].widget.toPlainText())

    def get_result(self):
        return self.duplicate_count, self.moved_duplicate_count