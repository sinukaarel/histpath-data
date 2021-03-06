import time

import pandas as pd
from matplotlib.patches import Ellipse
import numpy as np


def label_to_category_id(label):
    """
    Returns an ID from arbitrary label.
    """
    return {
        "label_color 1": 1,
        "label_color 2": 2,
        "label_color 3": 3,
        "label_color 4": 4,
        "label_color 5": 5,
    }[label]


def get_annotation_label(annotation):
    """
    Parses and returns actual label from annotation.
    """
    available_keys = [
        "label_color 1",
        "label_color 2",
        "label_color 3",
        "label_color 4",
        "label_color 5",
    ]

    keys = annotation["user_attrs"].keys()
    for key in keys:
        if key in available_keys:
            return key

    return None


def get_annotation_area(annotation):
    """
    Returns area under the ellipse.
    """
    return annotation["stats"]["area_px"]


def clamp(val, smallest, largest):
    return max(smallest, min(val, largest))


def calculate_bbox(annotation, top_left, image_size, downsample):
    """
    Calculates bbox [x, y, width, height] of annotated section relative to the image.

    ---
    annotation : array
        Single annotation element.
    top_left : tuple(x,y)
        Top left pixel of annotated image relative to the WSI.
    """
    ann_points = annotation["geometry"]["points"]
    x1, y1 = ann_points[0][0], ann_points[0][1]
    x2, y2 = ann_points[1][0], ann_points[1][1]

    # Points might be flipped.
    if x2 < x1:
        x2, x1 = x1, x2

    if y2 < y1:
        y2, y1 = y1, y2

    x1, y1 = x1 // downsample, y1 // downsample
    x2, y2 = x2 // downsample, y2 // downsample

    # Drawing points are relative to the top left
    # as the new image top left is (0,0)
    point1 = [x1 - top_left[0] // downsample, y1 - top_left[1] // downsample]
    point2 = [x2 - top_left[0] // downsample, y2 - top_left[1] // downsample]

    # Limit points to the image border.
    # That also limits bbox to image border.
    point1 = [
        clamp(point1[0], 0, image_size),
        clamp(point1[1], 0, image_size),
    ]
    point2 = [
        clamp(point2[0], 0, image_size),
        clamp(point2[1], 0, image_size),
    ]

    width = point2[0] - point1[0]
    height = point2[1] - point1[1]

    if width < 0 or height < 0:
        raise ValueError(
            "Annotation bbox width or height cant be negative!\n width:\t{}\n heigh:\t{}\n top-left:\t{}\n annotation:\t{}".format(
                width, height, top_left, annotation
            )
        )
    return [point1[0], point1[1], width, height]


def get_annotation_filename(annotation):
    """
    Returns filename of the image where annotation is made.
    """
    return "{}_lvl{}_{}_{}.png".format(
        annotation["filename"],
        annotation["lvl"],
        annotation["top_left"][0],
        annotation["top_left"][1],
    )


def create_COCO_annotations(tiles_with_annotation):
    """
    Creates COCO annotation from annotated tiles.
    """
    df = pd.DataFrame(tiles_with_annotation)
    coco = {}

    coco["info"] = {
        "description": "HistoPathology dataset",
        "url": "http://cocodataset.org",
        "version": "1.0",
        "year": 2021,
        "contributor": "Kaarel R",
        "date_created": time.asctime(),
    }

    coco["licenses"] = {}
    coco["images"] = []
    coco["annotations"] = []

    ann_id = 0
    for id, row in df.iterrows():
        im = {
            "license": 0,
            "file_name": get_annotation_filename(row),
            "coco_url": "",
            "height": row.image_size,
            "width": row.image_size,
            "date_captured": "2021-05-8 17:00:00",
            "flickr_url": "",
            "id": id,
        }

        prev_annotation = row.annotations
        for ann in prev_annotation:
            bbox = calculate_bbox(ann, row.top_left, row.image_size, row.downsample)
            coco_ann = {
                "id": ann_id,
                "image_id": id,
                "category_id": label_to_category_id(get_annotation_label(ann)),
                "segmentation": [],
                "area": get_annotation_area(ann),
                "bbox": bbox,
                "iscrowd": 0,
            }
            coco["annotations"].append(coco_ann)
            ann_id += 1

        coco["images"].append(im)

    coco["categories"] = [
        {"supercategory": "cell", "id": 1, "name": "Spermatogonia"},
        {"supercategory": "cell", "id": 2, "name": "Sertoli"},
        {"supercategory": "cell", "id": 3, "name": "Primary spermatocyte"},
        {"supercategory": "cell", "id": 4, "name": "Spermatid"},
        {"supercategory": "cell", "id": 5, "name": "Spermatozoa"},
    ]

    return coco
