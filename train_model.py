import os
import math
import json
import time
import argparse
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras import callbacks
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
try:
    # EfficientNetV2 may be available in newer TF versions
    from tensorflow.keras.applications.efficientnet_v2 import EfficientNetV2B0, preprocess_input as enet_v2_preprocess
except Exception:
    EfficientNetV2B0 = None
    enet_v2_preprocess = None
try:
    from tensorflow.keras.applications import EfficientNetB0, efficientnet
    from tensorflow.keras.applications.efficientnet import preprocess_input as enet_preprocess
except Exception:
    EfficientNetB0 = None
    enet_preprocess = None
import pickle
from sklearn.utils import class_weight
from sklearn.metrics import classification_report, confusion_matrix

# Configuration (defaults, override via CLI args)
IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 20
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BASE_DIR, 'fotky')
MODEL_PATH = os.path.join(BASE_DIR, 'NavigationApp', 'main', 'location_model.h5')
LABELS_PATH = os.path.join(BASE_DIR, 'NavigationApp', 'main', 'model_labels.pkl')
HISTORY_PATH = os.path.join(BASE_DIR, 'NavigationApp', 'main', 'training_history.json')

def prepare_data():
    """Prepare training data from fotky folder"""
    # Use preprocessing_function for MobileNetV2 and stronger augmentation
    datagen = ImageDataGenerator(
        preprocessing_function=preprocess_input,
        rotation_range=30,
        width_shift_range=0.2,
        height_shift_range=0.2,
        shear_range=0.2,
        zoom_range=0.2,
        brightness_range=(0.7, 1.3),
        horizontal_flip=True,
        fill_mode='nearest',
        validation_split=0.2
    )
    
    train_generator = datagen.flow_from_directory(
        PHOTOS_DIR,
        target_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='training'
    )
    
    validation_generator = datagen.flow_from_directory(
        PHOTOS_DIR,
        target_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='validation'
    )
    
    return train_generator, validation_generator


def apply_albumentations_batch(x_batch, alb_transform):
    # x_batch: numpy array HWC or NHWC with float images (pre-resize)
    out = np.empty_like(x_batch)
    for i in range(x_batch.shape[0]):
        img = x_batch[i]
        try:
            res = alb_transform(image=(img * 255).astype('uint8'))['image']
            out[i] = res.astype(np.float32) / 255.0
        except Exception:
            out[i] = img
    return out


def mixup_generator(generator, alpha=0.2):
    """Yield mixup-augmented batches from a DirectoryIterator"""
    while True:
        x, y = next(generator)
        lam = np.random.beta(alpha, alpha, x.shape[0])
        lam_x = lam.reshape(x.shape[0], 1, 1, 1)
        lam_y = lam.reshape(x.shape[0], 1)
        index = np.random.permutation(x.shape[0])
        x2, y2 = x[index], y[index]
        x_mix = x * lam_x + x2 * (1 - lam_x)
        y_mix = y * lam_y + y2 * (1 - lam_y)
        yield x_mix, y_mix

def create_model(num_classes):
    """Create a CNN model for image classification"""
    # Default backbone: MobileNetV2
    base_model = MobileNetV2(include_top=False, weights='imagenet', input_shape=(*IMAGE_SIZE, 3), pooling='avg')
    base_model.trainable = False  # freeze base for initial training

    x = base_model.output
    x = layers.Dense(512, activation='relu')(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(256, activation='relu')(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation='softmax')(x)

    model = keras.Model(inputs=base_model.input, outputs=outputs)

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss=keras.losses.CategoricalCrossentropy(label_smoothing=0.05),
        metrics=['accuracy']
    )

    return model, base_model


def create_model_with_backbone(num_classes, backbone='mobilenet', label_smoothing=0.05, focal=False):
    """Create model with selectable backbone (mobilenet, efficientnetv2, efficientnetb0)."""
    if backbone == 'efficientnetv2' and EfficientNetV2B0 is not None:
        base = EfficientNetV2B0(include_top=False, weights='imagenet', input_shape=(*IMAGE_SIZE, 3), pooling='avg')
    elif backbone == 'efficientnet' and EfficientNetB0 is not None:
        base = EfficientNetB0(include_top=False, weights='imagenet', input_shape=(*IMAGE_SIZE, 3), pooling='avg')
    else:
        base = MobileNetV2(include_top=False, weights='imagenet', input_shape=(*IMAGE_SIZE, 3), pooling='avg')

    base.trainable = False
    x = base.output
    x = layers.Dense(512, activation='relu')(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(256, activation='relu')(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation='softmax')(x)
    model = keras.Model(inputs=base.input, outputs=outputs)

    if focal:
        # Focal loss implementation
        def focal_loss(alpha=0.25, gamma=2.0):
            def loss_fn(y_true, y_pred):
                y_pred = tf.clip_by_value(y_pred, 1e-7, 1 - 1e-7)
                cross_entropy = -y_true * tf.math.log(y_pred)
                weight = alpha * tf.pow(1 - y_pred, gamma)
                loss = weight * cross_entropy
                return tf.reduce_sum(loss, axis=1)
            return loss_fn
        loss = focal_loss()
    else:
        loss = keras.losses.CategoricalCrossentropy(label_smoothing=label_smoothing)

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss=loss,
        metrics=['accuracy']
    )

    return model, base

def train_model(args):
    """Train the model and save it"""
    print("Preparing data...")
    train_generator, validation_generator = prepare_data()
    
    num_classes = len(train_generator.class_indices)
    print(f"Number of classes: {num_classes}")
    print(f"Class indices: {train_generator.class_indices}")
    
    print("Creating model...")
    model, base_model = create_model_with_backbone(num_classes, backbone=args.backbone, label_smoothing=args.label_smoothing, focal=args.focal_loss)
    model.summary()
    
    print("Training model...")
    # Callbacks
    cb = [
        callbacks.ModelCheckpoint(MODEL_PATH, save_best_only=True, monitor='val_loss'),
        callbacks.EarlyStopping(patience=args.patience, restore_best_weights=True, monitor='val_loss'),
        callbacks.ReduceLROnPlateau(factor=0.5, patience=3, verbose=1, monitor='val_loss')
    ]

    steps_per_epoch = max(1, train_generator.samples // args.batch_size)
    validation_steps = max(1, math.ceil(validation_generator.samples / args.batch_size))

    # Compute class weights to handle imbalance
    try:
        y_classes = train_generator.classes
        class_weights = class_weight.compute_class_weight('balanced', classes=np.unique(y_classes), y=y_classes)
        class_weights = {i: w for i, w in enumerate(class_weights)}
        print(f"Computed class weights: {class_weights}")
    except Exception:
        class_weights = None

    # For Python generators, Keras does not accept `class_weight` argument.
    # Create a generator that yields sample weights instead (x, y, sample_weight).
    def weighted_generator(generator, class_weights_map):
        while True:
            x_batch, y_batch = next(generator)
            # y_batch is one-hot; get class indices
            class_idxs = np.argmax(y_batch, axis=1)
            sample_weights = np.array([float(class_weights_map[int(ci)]) for ci in class_idxs], dtype=np.float32)
            yield x_batch, y_batch, sample_weights

    # Optionally use albumentations for stronger augmentation
    alb_transform = None
    if args.use_albumentations:
        try:
            import albumentations as A
            alb_transform = A.Compose([
                A.RandomBrightnessContrast(p=0.5),
                A.ShiftScaleRotate(shift_limit=0.1, scale_limit=0.15, rotate_limit=20, p=0.7),
                A.RandomRain(p=0.2),
                A.RandomShadow(p=0.2),
                A.HorizontalFlip(p=0.5)
            ])
            print('Using albumentations augmentation')
        except Exception:
            alb_transform = None
            print('albumentations not available — falling back to ImageDataGenerator')

    if args.mixup:
        train_input = mixup_generator(train_generator, alpha=args.mixup_alpha)
        use_sample_weights = False
    else:
        if class_weights is not None:
            if alb_transform is not None:
                # wrap generator to apply albumentations
                def alb_gen(gen, alb):
                    while True:
                        x, y = next(gen)
                        x = apply_albumentations_batch(x, alb)
                        class_idxs = np.argmax(y, axis=1)
                        sample_weights = np.array([float(class_weights[int(ci)]) for ci in class_idxs], dtype=np.float32)
                        yield x, y, sample_weights
                train_input = alb_gen(train_generator, alb_transform)
            else:
                train_input = weighted_generator(train_generator, class_weights)
            use_sample_weights = True
        else:
            if alb_transform is not None:
                def alb_gen2(gen, alb):
                    while True:
                        x, y = next(gen)
                        x = apply_albumentations_batch(x, alb)
                        yield x, y
                train_input = alb_gen2(train_generator, alb_transform)
            else:
                train_input = train_generator
            use_sample_weights = False

    fit_kwargs = dict(
        x=train_input,
        epochs=args.epochs,
        validation_data=validation_generator,
        steps_per_epoch=steps_per_epoch,
        validation_steps=validation_steps,
        callbacks=cb
    )

    # If using a weighted generator, Keras will receive sample weights from the generator output.
    history = model.fit(**fit_kwargs)
    
    # Save the model
    print(f"Saving model to {MODEL_PATH}")
    model.save(MODEL_PATH)
    
    # Save class labels
    print(f"Saving labels to {LABELS_PATH}")
    with open(LABELS_PATH, 'wb') as f:
        pickle.dump(train_generator.class_indices, f)

    # Save training history
    try:
        with open(HISTORY_PATH, 'w') as hf:
            json.dump({k: [float(x) for x in v] for k, v in history.history.items()}, hf)
        print(f"Saved training history to {HISTORY_PATH}")
    except Exception as e:
        print(f"Could not save history: {e}")
    
    print("Training complete!")
    if 'val_accuracy' in history.history:
        print(f"Final validation accuracy: {history.history['val_accuracy'][-1]:.4f}")
    elif 'val_acc' in history.history:
        print(f"Final validation accuracy: {history.history['val_acc'][-1]:.4f}")

    # Optional fine-tuning: unfreeze top layers
    if args.fine_tune_epochs > 0:
        print("Starting fine-tuning stage...")
        # Unfreeze the top `unfreeze_layers` layers of the base model
        try:
            # base_model should exist (returned by create_model)
            for layer in base_model.layers[-args.unfreeze_layers:]:
                layer.trainable = True
            model.compile(
                optimizer=keras.optimizers.Adam(learning_rate=args.fine_tune_lr),
                loss=keras.losses.CategoricalCrossentropy(label_smoothing=args.label_smoothing),
                metrics=['accuracy']
            )
            ft_history = model.fit(
                train_input,
                epochs=args.epochs + args.fine_tune_epochs,
                initial_epoch=args.epochs,
                validation_data=validation_generator,
                steps_per_epoch=steps_per_epoch,
                validation_steps=validation_steps,
                callbacks=cb
            )
            # update history dict
            for k, v in ft_history.history.items():
                history.history.setdefault(k, []).extend(v)
            # save fine-tuned model
            print(f"Saving fine-tuned model to {MODEL_PATH}")
            model.save(MODEL_PATH)
        except Exception as e:
            print(f"Fine-tuning failed: {e}")

    # Run evaluation on validation set and print detailed report
    try:
        print("Evaluating on validation set...")
        val_steps_all = math.ceil(validation_generator.samples / args.batch_size)
        preds = model.predict(validation_generator, steps=val_steps_all, verbose=1)
        y_pred = np.argmax(preds, axis=1)
        y_true = validation_generator.classes[:len(y_pred)]
        target_names = [k for k, v in sorted(train_generator.class_indices.items(), key=lambda x: x[1])]
        print(classification_report(y_true, y_pred, target_names=target_names))
        print("Confusion matrix:")
        print(confusion_matrix(y_true, y_pred))
    except Exception as e:
        print(f"Evaluation failed: {e}")

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--epochs', type=int, default=EPOCHS)
    p.add_argument('--batch-size', type=int, default=BATCH_SIZE)
    p.add_argument('--mixup', action='store_true')
    p.add_argument('--mixup-alpha', type=float, default=0.2)
    p.add_argument('--fine-tune-epochs', type=int, default=10)
    p.add_argument('--unfreeze-layers', type=int, default=50)
    p.add_argument('--fine-tune-lr', type=float, default=1e-4)
    p.add_argument('--label-smoothing', type=float, default=0.05)
    p.add_argument('--patience', type=int, default=7)
    p.add_argument('--backbone', choices=['mobilenet', 'efficientnet', 'efficientnetv2'], default='mobilenet')
    p.add_argument('--focal-loss', action='store_true')
    p.add_argument('--use-albumentations', action='store_true')
    return p.parse_args()


if __name__ == '__main__':
    args = parse_args()
    # Check if photos directory exists
    if not os.path.exists(PHOTOS_DIR):
        print(f"Error: Photos directory not found at {PHOTOS_DIR}")
        print("Please ensure the 'fotky' folder exists with subfolders for each location.")
        exit(1)

    # apply args to globals where needed
    BATCH_SIZE = args.batch_size
    EPOCHS = args.epochs

    train_model(args)
