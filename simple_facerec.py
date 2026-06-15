import face_recognition
import cv2
import os
import glob
import numpy as np

class SimpleFacerec:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []

        # Resize frame for a faster speed
        self.frame_resizing = 0.25

    def load_encoding_images(self, images_path):
        """
        Load encoding images from path
        :param images_path:
        :return:
        """
        # Load Images
        images_path = glob.glob(os.path.join(images_path, "*.*"))

        print("{} encoding images found.".format(len(images_path)))

        # Store image encoding and names
        for img_path in images_path:
            try:
                img = cv2.imread(img_path)
                if img is None:
                    continue
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                # Get the filename only from the initial file path.
                basename = os.path.basename(img_path)
                (filename, ext) = os.path.splitext(basename)
                
                # Get encoding safely
                encodings = face_recognition.face_encodings(rgb_img)
                if len(encodings) > 0:
                    img_encoding = encodings[0]
                    self.known_face_encodings.append(img_encoding)
                    self.known_face_names.append(filename)
                else:
                    print("Warning: No face found in {}, skipping.".format(img_path))
            except Exception as e:
                print("Error loading {}: {}".format(img_path, e))
        print("Encoding images loaded")

    def load_single_image(self, img_path):
        """
        Load a single image and append/replace its encoding dynamically.
        """
        try:
            img = cv2.imread(img_path)
            if img is None:
                return False
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            encodings = face_recognition.face_encodings(rgb_img)
            if len(encodings) > 0:
                img_encoding = encodings[0]
                basename = os.path.basename(img_path)
                (filename, ext) = os.path.splitext(basename)
                
                if filename in self.known_face_names:
                    idx = self.known_face_names.index(filename)
                    self.known_face_encodings[idx] = img_encoding
                else:
                    self.known_face_encodings.append(img_encoding)
                    self.known_face_names.append(filename)
                return True
            return False
        except Exception as e:
            print("Error loading single image {}: {}".format(img_path, e))
            return False


    def detect_known_faces(self, frame):
        small_frame = cv2.resize(frame, (0, 0), fx=self.frame_resizing, fy=self.frame_resizing)
        # Find all the faces and face encodings in the current frame of video
        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        face_names = []
        for face_encoding in face_encodings:
            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            name = "Unknown"

            # # If a match was found in known_face_encodings, just use the first one.
            # if True in matches:
            #     first_match_index = matches.index(True)
            #     name = known_face_names[first_match_index]

            # Or instead, use the known face with the smallest distance to the new face
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = self.known_face_names[best_match_index]
            face_names.append(name)

        # Convert to numpy array to adjust coordinates with frame resizing quickly
        face_locations = np.array(face_locations)
        face_locations = face_locations / self.frame_resizing
        return face_locations.astype(int), face_names
