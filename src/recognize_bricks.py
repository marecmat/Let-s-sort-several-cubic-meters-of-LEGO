import os
import time

from PIL import Image, ImageDraw, ImageFont
import requests

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "data"))
from config import BRICKOGNIZE_URL

def identify_lego_brick_from_image(image_path):
    """
    Send an image to Brickognize and return its JSON response.
    """

    with open(image_path, "rb") as file:
        response = requests.post(
            BRICKOGNIZE_URL,
            headers={
                "accept": "application/json"
            },
            files={
                "query_image": (
                    image_path,
                    file,
                    "image/jpeg"
                )
            }
        )

    if response.status_code == 200:
        return response.json()

    return {
        "error": (
            f"Request failed with status code "
            f"{response.status_code}"
        ),
        "details": response.text
    }


def remove_identified_brick_from_image(image_path, result):
    """
    Mask the brick identified by Brickognize so that the
    next Brickognize request can find another brick.
    """

    pad_frac = 0.20

    image = Image.open(image_path).convert("RGB")

    box = result["bounding_box"]

    width = int(box["image_width"])
    height = int(box["image_height"])

    image = image.resize((width, height))

    draw = ImageDraw.Draw(image)

    left = box["left"]
    upper = box["upper"]
    right = box["right"]
    lower = box["lower"]

    rect_width = right - left
    rect_height = lower - upper

    draw.rectangle(
        (
            left + rect_width * pad_frac,
            upper + rect_height * pad_frac,
            right - rect_width * pad_frac,
            lower - rect_height * pad_frac,
        ),
        fill=(0, 0, 0)
    )

    return image

def find_bricks(image_path):
    """
    Find multiple bricks in an image.

    Brickognize detects one brick at a time. After each successful
    detection, the detected region is covered and the modified
    image is sent back to Brickognize.

    Duplicate detections are filtered using the bounding box and
    confidence rather than just the brick ID, so two identical
    bricks can still be detected.
    """

    i = 0
    results = []

    original_image_path = image_path

    # Keep track of detections.
    detected_regions = []

    # Safety limit. This prevents pathological cases where
    # Brickognize keeps finding the same object forever.
    MAX_DETECTIONS = 100

    # If Brickognize becomes less confident than this, don't
    # continue trying to identify the same residual object.
    MIN_CONFIDENCE = 0.30

    # ------------------------------------------------------------
    # Temporary directory
    # ------------------------------------------------------------

    directory = os.path.dirname(
        image_path
    )

    if directory == "":
        directory = "."

    temp_directory = os.path.join(
        directory,
        "temp"
    )

    os.makedirs(
        temp_directory,
        exist_ok=True
    )

    current_image = image_path

    # ------------------------------------------------------------
    # Recognition loop
    # ------------------------------------------------------------

    while i < MAX_DETECTIONS:

        print(
            f"  Brickognize request #{i + 1}..."
        )

        result = identify_lego_brick_from_image(
            current_image
        )

        # --------------------------------------------------------
        # API error
        # --------------------------------------------------------

        if "error" in result:

            print(
                f"  Brickognize error: "
                f"{result['error']}"
            )

            break

        # --------------------------------------------------------
        # Nothing detected
        # --------------------------------------------------------

        items = result.get(
            "items",
            []
        )

        if not items:

            print(
                "  No more bricks found."
            )

            break

        item = items[0]

        brick_id = str(
            item.get("id", "")
        )

        brick_name = item.get(
            "name",
            "Unknown"
        )

        confidence = float(
            item.get("score", 0)
        )

        bbox = result.get(
            "bounding_box"
        )

        if not bbox:

            print(
                "  Detection has no bounding box."
            )

            break

        # --------------------------------------------------------
        # Confidence check
        # --------------------------------------------------------

        if confidence < MIN_CONFIDENCE:

            print(
                f"  Ignoring low-confidence result: "
                f"{brick_id} "
                f"({confidence:.1%})"
            )

            break

        # --------------------------------------------------------
        # Print result
        # --------------------------------------------------------

        print(
            f"  Found: {brick_id} - "
            f"{brick_name} "
            f"({confidence:.1%})"
        )

        # --------------------------------------------------------
        # Calculate normalized bounding box.
        #
        # This allows us to compare detections even though the
        # temporary images may have slightly different dimensions.
        # --------------------------------------------------------

        image_width = float(
            bbox["image_width"]
        )

        image_height = float(
            bbox["image_height"]
        )

        left = float(
            bbox["left"]
        ) / image_width

        right = float(
            bbox["right"]
        ) / image_width

        upper = float(
            bbox["upper"]
        ) / image_height

        lower = float(
            bbox["lower"]
        ) / image_height

        center_x = (
            left + right
        ) / 2

        center_y = (
            upper + lower
        ) / 2

        # --------------------------------------------------------
        # Detect repeated recognition of the same region.
        #
        # We intentionally DO NOT compare only the brick ID.
        #
        # Two 47844 bricks in the image are perfectly valid.
        # What we're looking for is the same brick being reported
        # again at essentially the same position.
        # --------------------------------------------------------

        duplicate = False

        for previous in detected_regions:

            distance_x = abs(
                center_x
                - previous["center_x"]
            )

            distance_y = abs(
                center_y
                - previous["center_y"]
            )

            # Difference in center position.
            distance = (
                distance_x ** 2
                + distance_y ** 2
            ) ** 0.5

            if distance < 0.08:

                # Same location AND same part.
                if (
                    previous["brick_id"]
                    == brick_id
                ):

                    duplicate = True
                    break

        if duplicate:

            print(
                f"  Duplicate detection ignored: "
                f"{brick_id}"
            )

            # Do NOT append the duplicate.
            #
            # Also don't keep modifying the image based on this
            # result. Doing so could create an infinite loop.
            break

        # --------------------------------------------------------
        # Store detection
        # --------------------------------------------------------

        detected_regions.append(
            {
                "brick_id": brick_id,
                "center_x": center_x,
                "center_y": center_y,
            }
        )

        results.append(
            result
        )

        # --------------------------------------------------------
        # Remove detected brick from image.
        # --------------------------------------------------------

        modified_image = (
            remove_identified_brick_from_image(
                current_image,
                result
            )
        )

        next_image = os.path.join(
            temp_directory,
            f"capture_{i}.{original_image_path.split('.')[-1]}"
        )

        modified_image.save(
            next_image,
            quality=100
        )

        current_image = next_image

        i += 1

    # ------------------------------------------------------------
    # Safety warning
    # ------------------------------------------------------------

    if i >= MAX_DETECTIONS:

        print(
            f"  Stopped after "
            f"{MAX_DETECTIONS} detections "
            f"(safety limit)."
        )

    return results

def show_bricks_found(results, image_path):
    """
    Draw all recognized bricks and their IDs on the original image.
    """

    image = Image.open(image_path).convert("RGB")

    if not results:
        return image

    first_box = results[0]["bounding_box"]

    image = image.resize(
        (
            int(first_box["image_width"]),
            int(first_box["image_height"])
        )
    )

    draw = ImageDraw.Draw(image)

    try:
        font_large = ImageFont.truetype(
            "../assets/arial.ttf",
            size=24
        )

        font_small = ImageFont.truetype(
            "../assets/arial.ttf",
            size=16
        )

    except OSError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    for result in results:

        box = result["bounding_box"]
        brick = result["items"][0]

        left = box["left"]
        upper = box["upper"]
        right = box["right"]
        lower = box["lower"]

        # Bounding box
        draw.rectangle(
            (
                left,
                upper,
                right,
                lower
            ),
            outline=(255, 0, 0),
            width=5
        )

        label = (
            f"{brick['id']} "
            f"({brick['score']:.0%})"
        )

        name = brick["name"]

        # Position label above the brick.
        text_x = left
        text_y = max(0, upper - 50)

        # ID
        bbox = draw.textbbox(
            (text_x, text_y),
            label,
            font=font_large
        )

        draw.rectangle(
            bbox,
            fill=(0, 0, 0)
        )

        draw.text(
            (text_x, text_y),
            label,
            font=font_large,
            fill=(255, 255, 255)
        )

        # Name
        name_y = text_y + 28

        bbox = draw.textbbox(
            (text_x, name_y),
            name,
            font=font_small
        )

        draw.rectangle(
            bbox,
            fill=(0, 0, 0)
        )

        draw.text(
            (text_x, name_y),
            name,
            font=font_small,
            fill=(255, 255, 255)
        )

    return image


def get_brick_feed(image_path):
    """
    Find all bricks in the image.

    Returns:
        annotated_image, results
    """

    results = find_bricks(image_path)

    if not results:
        return (
            Image.open(image_path).convert("RGB"),
            results
        )

    image = show_bricks_found(
        results,
        image_path
    )

    return image, results