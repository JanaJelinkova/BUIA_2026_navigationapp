from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import os
import pickle
import numpy as np
from PIL import Image
import io
from tensorflow import keras
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
import unicodedata
from .escape_instructions import get_instruction, get_location_name
from django.http import FileResponse, Http404

# Global variables for model and labels
model = None
class_indices = None
model_loaded = False

def load_model():
    """Load the trained model and class labels"""
    global model, class_indices, model_loaded
    if model_loaded:
        return True
    
    try:
        # settings.BASE_DIR already points to the outer NavigationApp directory,
        # so don't add 'NavigationApp' again when building paths to the app files.
        model_path = os.path.join(settings.BASE_DIR, 'main', 'location_model.h5')
        labels_path = os.path.join(settings.BASE_DIR, 'main', 'model_labels.pkl')
        
        if not os.path.exists(model_path):
            print(f"Model not found at {model_path}")
            return False
        
        model = keras.models.load_model(model_path)
        
        with open(labels_path, 'rb') as f:
            class_indices = pickle.load(f)
        
        # Reverse the class_indices to get index -> class name mapping
        class_indices = {v: k for k, v in class_indices.items()}
        model_loaded = True
        return True
    except Exception as e:
        print(f"Error loading model: {e}")
        return False

def homepage(request):
    return render(request, 'main/homepage.html')

@csrf_exempt
def api_classify(request):
    """API endpoint to classify camera image and return escape instructions"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    if not load_model():
        return JsonResponse({'error': 'Model not loaded. Please train the model first.'}, status=500)
    
    try:
        # Get image from request
        image_data = request.FILES.get('image')
        if not image_data:
            return JsonResponse({'error': 'No image provided'}, status=400)
        
        # Read and process image
        image = Image.open(image_data)
        image = image.convert('RGB')
        image = image.resize((224, 224))
        # Match training preprocessing (MobileNetV2 preprocess_input)
        image_array = np.array(image).astype(np.float32)
        image_array = np.expand_dims(image_array, axis=0)
        image_array = preprocess_input(image_array)

        # Test-time augmentation: average prediction over original and horizontally flipped image
        try:
            preds = []
            preds.append(model.predict(image_array))
            flipped = np.flip(image_array, axis=2)
            preds.append(model.predict(flipped))
            predictions = np.mean(preds, axis=0)
        except Exception:
            # Fallback to single prediction
            predictions = model.predict(image_array)
        predicted_class_index = np.argmax(predictions[0])
        confidence = float(predictions[0][predicted_class_index])
        
        # Get location key (may contain diacritics from folder names)
        location_key = class_indices.get(predicted_class_index, 'unknown')

        # Normalize key: remove diacritics and lowercase to match keys in escape_instructions
        def normalize_key(s):
            try:
                s = s or ''
                nfkd = unicodedata.normalize('NFD', s)
                return ''.join([c for c in nfkd if unicodedata.category(c) != 'Mn']).lower()
            except Exception:
                return (s or '').lower()

        norm_key = normalize_key(location_key)
        # Special-case mappings for names with diacritics or alternative folder names
        # e.g. 'skříňky' will normalize to variants like 'skrinky' or 'skrinky', so detect by substring
        norm_key_mapped = norm_key
        if 'skrin' in norm_key or 'skri' in norm_key:
            norm_key_mapped = 'skrinky'
        if norm_key.lower() == 'rai' or norm_key.lower() == 'rai.':
            norm_key_mapped = 'rai'
        location_name = get_location_name(norm_key_mapped)
        instruction = get_instruction(norm_key_mapped)

        # Choose plan image from either repo-level plans/ or fotky/plans. Default to default.png
        repo_plans = os.path.normpath(os.path.join(settings.BASE_DIR, '..', 'plans'))
        fotky_plans = os.path.normpath(os.path.join(settings.BASE_DIR, '..', 'fotky', 'plans'))
        if os.path.exists(repo_plans):
            plans_dir = repo_plans
        else:
            plans_dir = fotky_plans

        plan_filename = 'default.png'
        try:
            # map normalized keys to filenames (use simple lowercase match)
            plan_candidates = {
                'ucebna': 'učebna.png',
                'chodba': 'chodba.png',
                'schodiste': 'schody.png',
                'turnikety': 'turnikety.png',
                'venek': 'venek.png',
                'skrinky': 'default.png',
                'rai': 'RAI.png'
            }
            candidate = plan_candidates.get(norm_key_mapped)
            if candidate:
                candidate_path = os.path.join(plans_dir, candidate)
                if os.path.exists(candidate_path):
                    plan_filename = candidate
        except Exception:
            plan_filename = 'default.png'

        return JsonResponse({
            'location': location_name,
            'location_key': location_key,
            'location_key_normalized': norm_key_mapped,
            'instruction': instruction,
            'plan': plan_filename,
            'confidence': confidence
        })
        
    except Exception as e:
        print(f"Error during classification: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def api_reload_model(request):
    """Reload the model from disk. Restricted to POST from localhost."""
    global model_loaded
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    # Permit only local calls for safety
    remote = request.META.get('REMOTE_ADDR')
    if remote not in ('127.0.0.1', '::1'):
        return JsonResponse({'error': 'Not allowed'}, status=403)

    model_loaded = False
    ok = load_model()
    return JsonResponse({'reloaded': ok})


def api_plan(request, filename):
    """Serve small plan images from fotky/plans directory."""
    try:
        # Check repo-level plans/ first, then fotky/plans
        repo_plans = os.path.normpath(os.path.join(settings.BASE_DIR, '..', 'plans'))
        fotky_plans = os.path.normpath(os.path.join(settings.BASE_DIR, '..', 'fotky', 'plans'))
        plans_dir = repo_plans if os.path.exists(repo_plans) else fotky_plans
        safe_name = os.path.basename(filename)
        file_path = os.path.join(plans_dir, safe_name)
        if not os.path.exists(file_path):
            # fallback to default if present
            default_path = os.path.join(plans_dir, 'default.png')
            if os.path.exists(default_path):
                return FileResponse(open(default_path, 'rb'), content_type='image/png')
            raise Http404('Plan not found')
        return FileResponse(open(file_path, 'rb'), content_type='image/png')
    except Http404:
        raise
    except Exception as e:
        print(f"Error serving plan {filename}: {e}")
        raise Http404('Plan error')