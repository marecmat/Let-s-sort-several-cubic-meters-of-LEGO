import os
import requests
from PIL import Image, ImageDraw, ImageFont

def identify_lego_brick_from_image(image_path):
    # https://www.reddit.com/r/learnpython/comments/11pa4gz/brickognize_api/
    url = 'https://api.brickognize.com/predict/'
    with open(image_path, 'rb') as file:
        response = requests.post(
            url, 
            headers={'accept': 'application/json'}, 
            files={'query_image': (image_path, file, 'image/jpeg')})

    if response.status_code == 200:
        return response.json()
    
    else:
        return {
            'error': f'Request failed with status code {response.status_code}', 
            'details': response.text
        }



def remove_identified_bricks_from_image(image_path, result):
    pad_frac = .2 # max = .5
    im = Image.open(image_path)
    width = int(result['bounding_box']['image_width'])
    height = int(result['bounding_box']['image_height'])
    im = im.resize((width, height))
    draw = ImageDraw.Draw(im)
    rect_length = result['bounding_box']['right'] - result['bounding_box']['left']
    rect_height = result['bounding_box']['lower'] - result['bounding_box']['upper']
    draw.rectangle(
        (
            result['bounding_box']['left'] + rect_length*pad_frac, 
            result['bounding_box']['upper'] + rect_height*pad_frac, 
            result['bounding_box']['right'] - rect_length*pad_frac, 
            result['bounding_box']['lower'] - rect_height*pad_frac
        ), 
        fill=(0, 0, 0)
    )

    return im



def find_bricks(image_path):
    i = 0
    id_stored = []
    results = []
    result = {'items': ['dummy element']}
    image = image_path
    if not os.path.exists(image_path.split("/")[0] + '/temp/'):
        os.mkdir(image_path.split("/")[0] + '/temp/')
    while True:
        # print(image)
        result = identify_lego_brick_from_image(image)
        if len(result['items']) == 0:
            break
        elif result['items'][0]['id'] in id_stored:
            break
        else:
            print(f"found brick id, {result['items'][0]['id']}")
            im = remove_identified_bricks_from_image(image, result)
            # Image._show(im)
            image = f'{image_path.split("/")[0]}/temp/{image_path.split("/")[1].split(".")[0]}_{i}.{image_path.split(".")[-1]}'
            im.save(image, quality=100)    
            i += 1
            results.append(result)
            id_stored.append(result['items'][0]['id'])    
    return results


def show_bricks_found(results, image_path):
    """
    TODO
    Show the bricks found in the image by writing their name, id and location on the image.
    Part of the GUI to be done
    """
    im = Image.open(image_path)
    im = im.resize((
        int(results[0]['bounding_box']['image_width']), 
        int(results[0]['bounding_box']['image_height'])
    ))
    draw = ImageDraw.Draw(im)

    
    pad = 8
    for result in results[1:]:
        draw.rectangle(
            (
                result['bounding_box']['left'], 
                result['bounding_box']['upper'], 
                result['bounding_box']['right'], 
                result['bounding_box']['lower']
            ), 
            outline=(255, 0, 0), width=5, fill=None
        )

        text_format = {
            'align': 'center', 
            'anchor': 'ms',
            'fill': (255, 255, 255), 
            'stroke_width': 3, 
            'stroke_fill':(0, 0, 0), 
        }

        draw.text(
            ((result['bounding_box']['left'] + result['bounding_box']['right'])/2, result['bounding_box']['upper']-pad), 
            f"{result['items'][0]['id']}", 
            font=ImageFont.truetype("../assets/arial.ttf", size=24), **text_format)
        
        draw.text(
            ((result['bounding_box']['left'] + result['bounding_box']['right'])/2, result['bounding_box']['lower']-pad), 
            f"{result['items'][0]['name']}", 
            font=ImageFont.truetype("../assets/arial.ttf", size=12), **text_format)
    Image._show(im)
    # return im
