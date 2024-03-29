import cv2
import dlib

from src.object_detection.object_detection_runner import ObjectDetector
from settings import MARGIN, WEB_CAM, TRACK_CYCLE, LOCAL
from src.data_processing.data_import import ImportData


class BeverageCounter:

    def __init__(self):

        self.beverage_trackers = {}
        self.current_beverage_id = 1
        self.beverage_names = {}
        self.beverage_attributes = {}
        self.obj_detector = ObjectDetector()
        self.data_importer = ImportData()

    def detect_beverages(self, img):

        _, coordinates, obj_descriptions = self.obj_detector.detect_object(img)
        obj_attr = ""
        for rect, obj_des in zip(coordinates, obj_descriptions):
            if obj_des == 1.0:
                obj_attr = "water"
            elif obj_des == 2.0:
                obj_attr = "cocacola"
            elif obj_des == 3.0:
                obj_attr = "pepsi"

            left = rect[0]
            top = rect[1]
            right = rect[2]
            bottom = rect[3]
            cv2.rectangle(img, (left, top), (right, bottom), (0, 0, 255), 2)
            x_bar = 0.5 * (left + right)
            y_bar = 0.5 * (top + bottom)

            matched_fid = None

            for fid in self.beverage_trackers.keys():

                tracked_position = self.beverage_trackers[fid].get_position()
                t_left = int(tracked_position.left())
                t_top = int(tracked_position.top())
                t_right = int(tracked_position.right())
                t_bottom = int(tracked_position.bottom())

                # calculate the center point
                t_x_bar = 0.5 * (t_left + t_right)
                t_y_bar = 0.5 * (t_top + t_bottom)

                # check if the center point of the face is within the rectangleof a tracker region.
                # Also, the center point of the tracker region must be within the region detected as a face.
                # If both of these conditions hold we have a match

                if ((t_left <= x_bar <= (t_left + t_right)) and (t_top <= y_bar <= (t_top + t_bottom)) and
                        (left <= t_x_bar <= right) and (top <= t_y_bar <= bottom)):
                    matched_fid = fid
                    # If no matched fid, then we have to create a new tracker
            if matched_fid is None:
                print("Creating new tracker " + str(self.current_beverage_id))
                # Create and store the tracker
                tracker = dlib.correlation_tracker()
                tracker.start_track(img, dlib.rectangle(left - MARGIN, top - MARGIN, right + MARGIN,
                                                        bottom + MARGIN))
                self.beverage_trackers[self.current_beverage_id] = tracker
                # time.sleep(0.1)
                self.beverage_attributes[self.current_beverage_id] = [str(self.current_beverage_id), obj_attr]

                # Increase the currentFaceID counter
                self.current_beverage_id += 1

        return

    def track_beverages(self, beverage_image):

        for fid in self.beverage_trackers.keys():
            tracked_position = self.beverage_trackers[fid].get_position()
            t_left = int(tracked_position.left())
            t_top = int(tracked_position.top())
            t_right = int(tracked_position.right())
            t_bottom = int(tracked_position.bottom())

            cv2.rectangle(beverage_image, (t_left, t_top), (t_right, t_bottom), (0, 0, 255), 2)

            cv2.putText(beverage_image, str(self.beverage_attributes[fid][1]), (int(t_right), int(t_top)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        return beverage_image

    def main(self, video_path=None):

        init_waters = 0
        init_cocacolas = 0
        init_pepsis = 0
        suit_count = 0

        if WEB_CAM:
            cap = cv2.VideoCapture(0)
        else:
            cap = cv2.VideoCapture(video_path)
        cnt = 0

        while True:

            ret, img = cap.read()
            # img = self.detect_one_frame(img=img)
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
            result_image = img.copy()
            cnt += 1
            fids_to_delete = []
            for fid in self.beverage_trackers.keys():
                tracking_quality = self.beverage_trackers[fid].update(img)

                # If the tracking quality is good enough, we must delete
                # this tracker
                if tracking_quality < 7:
                    fids_to_delete.append(fid)

            for fid in fids_to_delete:
                print("Removing fid " + str(fid) + " from list of trackers")
                self.beverage_trackers.pop(fid, None)
                self.beverage_attributes.pop(fid, None)

            if cnt % TRACK_CYCLE == 0:
                self.detect_beverages(img=img)
            else:
                result_image = self.track_beverages(beverage_image=result_image)

            if LOCAL:
                waters = 0
                cocacolas = 0
                pepsis = 0
                for idx in self.beverage_attributes.keys():
                    if self.beverage_attributes[idx][1] == "water":
                        waters += 1
                    elif self.beverage_attributes[idx][1] == "cocacola":
                        cocacolas += 1
                    if self.beverage_attributes[idx][1] == "pepsi":
                        pepsis += 1
                cv2.putText(result_image, 'Water: {}'.format(str(waters)), (20, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                cv2.putText(result_image, 'Coca cola: {}'.format(str(cocacolas)), (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                cv2.putText(result_image, 'Pepsi: {}'.format(str(pepsis)), (20, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                cv2.imshow("image", result_image)

                if abs(init_cocacolas - cocacolas) == 0 and abs(init_waters - waters) == 0 and \
                        abs(init_pepsis - pepsis) == 0:
                    suit_count += 1
                else:
                    suit_count = 0

                init_pepsis = pepsis
                init_waters = waters
                init_cocacolas = cocacolas

                if suit_count == TRACK_CYCLE * 5 and len(self.beverage_attributes.keys()) != 0:
                    self.data_importer.import_parsing_data(barcode="", types=["water", "coca cola", "pepsi"],
                                                           amounts=[init_waters, init_cocacolas, init_pepsis])

                if cv2.waitKey(1) & 0xFF == ord('q'):  # press q to quit
                    break
        # kill open cv things
        cap.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    BeverageCounter().main()
