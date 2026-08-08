import os
import sys
from pathlib import Path

import cv2
from PIL import Image
from numpy import array, uint8

from recognize_bricks import get_brick_feed
from db_lookup import load_database, print_batch_results
sys.path.append(str(Path(__file__).parent.parent / "data"))
from config import TEMP_DIRECTORY, TEMP_IMAGE_PATH, WINDOW_NAME

def save_frame(frame):
    """
    Save an OpenCV BGR frame as a correctly colored RGB JPEG.

    OpenCV uses BGR.
    PIL uses RGB.

    Without this conversion, red and blue are swapped.
    """

    frame_rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    image = Image.fromarray(
        frame_rgb.astype(uint8)
    )

    os.makedirs(
        TEMP_DIRECTORY,
        exist_ok=True
    )

    image.save(
        TEMP_IMAGE_PATH,
        quality=95
    )


def display_pil_image(image):
    """
    Display a PIL RGB image using OpenCV.

    OpenCV expects BGR, so convert RGB -> BGR.
    """

    image_array = array(image)

    image_bgr = cv2.cvtColor(
        image_array,
        cv2.COLOR_RGB2BGR
    )

    cv2.imshow(
        WINDOW_NAME,
        image_bgr
    )


def webcam_feed():

    database = load_database()

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():

        print(
            "ERROR: Could not open webcam."
        )

        return

    print()
    print("=" * 70)
    print("LEGO SORTER")
    print("=" * 70)
    print()
    print("SPACE  Capture and identify bricks")
    print("ESC    Quit")
    print()
    print("=" * 70)
    print()

    while True:

        success, frame = camera.read()

        if not success:

            print(
                "ERROR: Could not read webcam frame."
            )

            break

        # Live camera feed.
        cv2.imshow(
            WINDOW_NAME,
            frame
        )

        key = cv2.waitKey(20) & 0xFF

        # ESC
        if key == 27:
            break

        # SPACE
        if key == 32:

            print()
            print("=" * 70)
            print("CAPTURED")
            print("=" * 70)

            # Save current frame with correct colors.
            save_frame(frame)

            print(
                f"Image saved to "
                f"{TEMP_IMAGE_PATH}"
            )

            print()
            print(
                "Searching for bricks..."
            )

            try:

                annotated_image, results = (
                    get_brick_feed(
                        TEMP_IMAGE_PATH
                    )
                )

                # Display the original image with
                # all detected bricks marked.
                display_pil_image(
                    annotated_image
                )

                # Find possible set destinations.
                print_batch_results(
                    database,
                    results
                )

                print(
                    "Press SPACE to scan another "
                    "batch, or ESC to quit."
                )

            except Exception as error:

                print()
                print(
                    "ERROR while processing image:"
                )

                print(error)

                print()

    camera.release()

    cv2.destroyAllWindows()


if __name__ == "__main__":
    webcam_feed()