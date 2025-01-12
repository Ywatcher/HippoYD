import os
import random
import tempfile

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy
import numpy as np
import tensorflow as tf
from sklearn.metrics import roc_curve, auc
from tensorflow import keras
from tensorflow.keras import backend as K
from tensorflow.keras import layers

from yawn_train.src.model_config import IMAGE_PAIR_SIZE


# plot diagnostic learning curves


# https://medium.com/edureka/tensorflow-image-classification-19b63b7bfd95
# https://www.tensorflow.org/hub/tutorials/tf2_text_classification
# https://keras.io/examples/vision/image_classification_from_scratch/
# https://www.kaggle.com/darthmanav/dog-vs-cat-classification-using-cnn
# Input Layer: It represent input image data. It will reshape image into single diminsion array. Example your image is 100x100=10000, it will convert to (100,1) array.
# Conv Layer: This layer will extract features from image.
# Pooling Layer: This layer reduces the spatial volume of input image after convolution.
# Fully Connected Layer: It connect the network from a layer to another layer
# Output Layer: It is the predicted values layer.
def gray_to_rgb(img):
    return np.repeat(img, 3, 2)


def plot_data_generator_first_20(train_generator):
    img_list = []
    for file in train_generator.filepaths[:20]:
        img = tf.keras.preprocessing.image.load_img(file)
        img_list.append(img)

    columns = 4
    rows = 5
    fig = plt.gcf()
    fig.set_size_inches(columns * 4, rows * 4)
    for i in range(1, columns * rows + 1):
        plt.subplot(rows, columns, i)
        img = img_list[i - 1]
        plt.imshow(img)
    plt.show()


def predict_image(model, input_img, grayscale: bool):
    loaded_img = keras.preprocessing.image.load_img(
        input_img,
        target_size=IMAGE_PAIR_SIZE,
        color_mode='grayscale' if grayscale else 'rgb'
    )
    img_array = keras.preprocessing.image.img_to_array(loaded_img)
    # scale pixel values to [0, 1]
    img_array = img_array.astype(np.float32)
    img_array /= 255.0
    img_array = tf.expand_dims(img_array, 0)  # Create batch axis

    model_predictions = model.predict(img_array)
    score = model_predictions[0]
    print(
        "This image (%s) is %.2f %% opened."
        % (input_img, 100 * score)
    )


def show_pred_actual_lables(fig_dst, predictions, test_labels, test_images, class_names, class_indices):
    # Plot the first X test images, their predicted labels, and the true labels.
    # Color correct predictions in blue and incorrect predictions in red.
    num_rows = 10
    num_cols = 3
    num_images = num_rows * num_cols
    plt.figure(figsize=(2 * 2 * num_cols, 2 * num_rows))
    for i in range(num_images):
        idx = random.choice(range(len(predictions)))
        plt.subplot(num_rows, 2 * num_cols, 2 * i + 1)
        is_correct_pred = plot_image(idx, predictions[idx], test_labels, test_images, class_names,
                                     class_indices)
        plt.subplot(num_rows, 2 * num_cols, 2 * i + 2)
        plot_value_array(predictions[idx], is_correct_pred)
    plt.tight_layout()
    plt.savefig(fig_dst)
    plt.show()


def plot_image(i, predictions_item, true_label_id, images, class_names, class_indices) -> bool:
    true_label_id, img = true_label_id[i], images[i]
    plt.grid(False)
    plt.xticks([])
    plt.yticks([])

    img_filename = os.path.basename(img)
    img_obj = mpimg.imread(img)
    plt.imshow(img_obj, cmap="gray")
    # predicted_label_id = np.argmax(predictions_item)  # take class with highest confidence
    predicted_confidence = np.max(predictions_item)
    predicted_score = 100 * predicted_confidence

    is_mouth_opened = True if predicted_confidence >= 0.2 else False
    # classes taken from input data
    predicted_label_id = class_indices['opened' if is_mouth_opened else 'closed']

    predicted_class = class_names[predicted_label_id]
    is_correct_prediction = predicted_label_id == true_label_id
    if is_correct_prediction:
        color = 'blue'
    else:
        color = 'red'
    plt.xlabel("{}, {} {:2.0f}% ({})".format(img_filename, predicted_class,
                                             predicted_score,
                                             class_names[true_label_id]),
               color=color)
    return is_correct_prediction


def plot_value_array(predictions_array, is_correct_prediction: bool):
    plt.grid(False)
    plt.xticks([])
    plt.yticks([])
    predicted_confidence = np.max(predictions_array)
    thisplot = plt.bar(range(1), predicted_confidence, color="#777777")
    plt.ylim([0, 1])
    predicted_label = np.argmax(predictions_array)
    if is_correct_prediction:
        color = 'blue'
    else:
        color = 'red'
    thisplot[predicted_label].set_color(color)


def summarize_diagnostics(
        history_dict, plot_accuracy_path, plot_loss_path, plot_lr_path):
    acc = history_dict['accuracy']
    val_acc = history_dict['val_accuracy']
    loss = history_dict['loss']
    val_loss = history_dict['val_loss']
    epochs = range(1, len(acc) + 1)

    if 'lr' in history_dict:
        learning_rate = history_dict['lr']
        plt.plot(epochs, learning_rate, 'b', label='Learning rate')
        plt.minorticks_on()
        plt.grid(which='major')
        plt.grid(which='minor', linestyle=':')
        plt.title('Learning rate')
        plt.xlabel('Epochs')
        plt.ylabel('LR')
        plt.legend()
        plt.savefig(plot_lr_path)
        plt.show()
        plt.clf()  # clear figure

    # Plot Epochs / Training and validation loss
    # "r" is for "solid red line"
    plt.plot(epochs, loss, 'b', label='Training loss')
    # b is for "solid blue line"
    plt.plot(epochs, val_loss, 'r', label='Validation loss')

    plt.minorticks_on()
    plt.grid(which='major')
    plt.grid(which='minor', linestyle=':')

    plt.title('Training and validation loss (Cross Entropy Loss)')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()

    plt.savefig(plot_loss_path)
    plt.show()

    # Plot Epochs / Training and validation accuracy
    plt.clf()  # clear figure

    plt.plot(epochs, acc, 'b', label='Training acc')
    plt.plot(epochs, val_acc, 'r', label='Validation acc')

    plt.minorticks_on()
    plt.grid(which='major')
    plt.grid(which='minor', linestyle=':')

    plt.title('Training and validation accuracy (Classification Accuracy)')
    plt.xlabel('Epochs')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.savefig(plot_accuracy_path)
    plt.show()


def recall_m(y_true, y_pred):
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
    recall = true_positives / (possible_positives + K.epsilon())
    return recall


def precision_m(y_true, y_pred):
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
    precision = true_positives / (predicted_positives + K.epsilon())
    return precision


def f1_m(y_true, y_pred):
    precision = precision_m(y_true, y_pred)
    recall = recall_m(y_true, y_pred)
    return 2 * ((precision * recall) / (precision + recall + K.epsilon()))


# This is a sample of a scheduler I used in the past
def lr_scheduler(epoch, lr):
    decay_rate = 0.85
    decay_step = 1
    if epoch % decay_step == 0 and epoch:
        return lr * pow(decay_rate, np.floor(epoch / decay_step))
    return lr


# Define the Required Callback Function
class printlearningrate(tf.keras.callbacks.Callback):
    def on_epoch_end(self, epoch, logs={}):
        optimizer = self.model.optimizer
        lr = K.eval(optimizer.lr)
        epoch_count = epoch + 1
        print('\n', "Epoch:", epoch_count, ', LR: {:.2f}'.format(lr))


# Taken from https://github.com/AvinashNath2/Image-Classification-using-Keras
def create_compiled_model_lite(input_shape, opt=keras.optimizers.Adam(lr=0.001)) -> keras.Model:
    model = keras.Sequential()
    model.add(layers.Convolution2D(32, (3, 3), input_shape=input_shape))
    model.add(layers.Activation('relu'))
    model.add(layers.MaxPooling2D(pool_size=(2, 2)))

    model.add(layers.Convolution2D(32, (3, 3)))
    model.add(layers.Activation('relu'))
    model.add(layers.MaxPooling2D(pool_size=(2, 2)))

    model.add(layers.Convolution2D(64, (3, 3)))
    model.add(layers.Activation('relu'))
    model.add(layers.MaxPooling2D(pool_size=(2, 2)))

    model.add(layers.Flatten())
    model.add(layers.Dense(64))
    model.add(layers.Activation('relu'))
    model.add(layers.Dropout(0.5))
    model.add(layers.Dense(1))
    model.add(layers.Activation('sigmoid'))

    # compile model
    model.compile(optimizer=opt, loss='binary_crossentropy',
                  metrics=['accuracy', f1_m, precision_m, recall_m])
    return model


def create_compiled_model_mobilenet2(input_shape, opt=keras.optimizers.Adam(lr=0.001)) -> keras.Model:
    model = keras.Sequential()
    model.add(keras.applications.MobileNetV2(
        include_top=False, weights="imagenet", input_shape=input_shape))
    model.add(tf.keras.layers.GlobalAveragePooling2D())
    model.add(layers.Dense(1, activation='sigmoid'))
    model.layers[0].trainable = False  # Freeze the convolutional base

    # compile model
    model.compile(optimizer=opt, loss='binary_crossentropy',
                  metrics=['accuracy', f1_m, precision_m, recall_m])
    return model


def create_compiled_model_vgg16(input_shape, opt=keras.optimizers.Adam(lr=0.001)) -> keras.Model:
    vgg16_base = tf.keras.applications.VGG16(input_shape=input_shape, include_top=False, weights='imagenet')

    model = keras.Sequential()
    model.add(vgg16_base)
    model.add(tf.keras.layers.GlobalAveragePooling2D())
    model.add(layers.Dense(1, activation='sigmoid'))
    model.layers[0].trainable = False  # Freeze the convolutional base

    # compile model
    model.compile(optimizer=opt, loss='binary_crossentropy',
                  metrics=['accuracy', f1_m, precision_m, recall_m])
    return model


def create_flowernet(input_shape, opt=keras.optimizers.Adam(lr=0.001)) -> keras.Model:
    model = tf.keras.models.Sequential()
    model.add(layers.Conv2D(16, (3, 3),
                            input_shape=input_shape,  # dimensions = 100X100, color channel = B&W
                            activation='relu'))
    model.add(layers.MaxPooling2D(2, 2))
    model.add(layers.Conv2D(32, (3, 3), activation='relu'))
    model.add(layers.MaxPooling2D(2, 2))
    model.add(layers.Conv2D(64, (3, 3), activation='relu'))
    model.add(layers.MaxPooling2D(2, 2))
    model.add(layers.Conv2D(64, (3, 3), activation='relu'))
    model.add(layers.MaxPooling2D(2, 2))
    model.add(layers.Flatten())
    model.add(layers.Dense(512, activation='relu'))
    model.add(layers.Dense(1, activation='sigmoid'))

    # compile model
    model.compile(optimizer=opt, loss='binary_crossentropy',
                  metrics=['accuracy', f1_m, precision_m, recall_m])
    return model


def create_alexnet(input_shape, opt=keras.optimizers.Adam(lr=0.001)) -> keras.Model:
    model_alexnet = keras.Sequential()
    # 1st Convolutional Layer
    model_alexnet.add(layers.Conv2D(32, (3, 3),
                                    input_shape=input_shape,  # dimensions = 100X100, color channel = B&W
                                    padding='same',
                                    activation='relu'))
    # pooling
    model_alexnet.add(layers.MaxPooling2D(pool_size=(2, 2), padding='same'))
    model_alexnet.add(layers.BatchNormalization())
    # 2nd Convolutional Layer
    model_alexnet.add(layers.Conv2D(64, (3, 3),
                                    padding='same',
                                    activation='relu'))
    # pooling
    model_alexnet.add(layers.MaxPooling2D(pool_size=(2, 2), padding='same'))
    model_alexnet.add(layers.BatchNormalization())

    # 3rd Convolutional Layer
    model_alexnet.add(layers.Conv2D(64, (3, 3),
                                    padding='same',
                                    activation='relu'))
    model_alexnet.add(layers.BatchNormalization())
    # 4th Convolutional Layer
    model_alexnet.add(layers.Conv2D(128, (3, 3),
                                    padding='same',
                                    activation='relu'))
    model_alexnet.add(layers.BatchNormalization())
    # 5th Convolutional Layer
    model_alexnet.add(layers.Conv2D(128, (3, 3),
                                    padding='same',
                                    activation='relu'))
    # pooling
    model_alexnet.add(layers.MaxPooling2D(pool_size=(3, 3), padding='same'))
    model_alexnet.add(layers.BatchNormalization())
    # Flatten
    model_alexnet.add(layers.Flatten())
    # 1st Dense Layer
    model_alexnet.add(layers.Dense(128,
                                   activation='relu', kernel_initializer='glorot_uniform'))
    model_alexnet.add(layers.Dropout(0.10))
    model_alexnet.add(layers.BatchNormalization())
    # 2nd Dense Layer
    model_alexnet.add(layers.Dense(256,
                                   activation='relu', kernel_initializer='glorot_uniform'))
    model_alexnet.add(layers.Dropout(0.20))
    model_alexnet.add(layers.BatchNormalization())
    # # 3rd Dense Layer
    model_alexnet.add(layers.Dense(512,
                                   activation='relu', kernel_initializer='glorot_uniform'))
    model_alexnet.add(layers.Dropout(0.2))
    model_alexnet.add(layers.BatchNormalization())
    # output layer
    model_alexnet.add(layers.Dense(1, activation='sigmoid'))
    # Compile
    model_alexnet.compile(loss='binary_crossentropy', optimizer=opt,
                          metrics=['accuracy'])
    return model_alexnet


def create_compiled_model(input_shape, opt=keras.optimizers.Adam(lr=0.001)) -> keras.Model:
    # Note that when using the delayed-build pattern (no input shape specified),
    # the model gets built the first time you call `fit`, `eval`, or `predict`,
    # or the first time you call the model on some input data.
    model = keras.Sequential()
    model.add(layers.Conv2D(32, (3, 3), activation='relu', kernel_initializer='he_uniform', padding='same',
                            input_shape=input_shape))
    model.add(layers.MaxPooling2D((2, 2)))
    model.add(layers.Dropout(0.2))  # Layer 1
    model.add(layers.Conv2D(64, (3, 3), activation='relu', kernel_initializer='he_uniform', padding='same'))
    model.add(layers.MaxPooling2D((2, 2)))
    model.add(layers.Dropout(0.2))  # Layer 2
    model.add(layers.Conv2D(128, (3, 3), activation='relu', kernel_initializer='he_uniform', padding='same'))
    model.add(layers.MaxPooling2D((2, 2)))
    model.add(layers.Dropout(0.2))  # Layer 3
    model.add(layers.Flatten())  # Fully connected layer
    model.add(layers.Dense(128, activation='relu', kernel_initializer='he_uniform'))  # Fully connected layer
    model.add(layers.Dropout(0.5))  # Fully connected layer
    model.add(layers.Dense(1, activation='sigmoid'))  # Fully connected layer
    # compile model
    model.compile(optimizer=opt, loss='binary_crossentropy',
                  metrics=['accuracy', f1_m, precision_m, recall_m])
    return model


def evaluate_model(interpreter, test_images, test_labels):
    input_index = interpreter.get_input_details()[0]["index"]
    output_index = interpreter.get_output_details()[0]["index"]
    floating_model = interpreter.get_input_details()[0]['dtype'] == np.float32

    # Run predictions on ever y image in the "test" dataset.
    prediction_confs = []
    class_indices = {'closed': 0, 'opened': 1}
    for i, test_image in enumerate(test_images):
        if i % 1000 == 0:
            print('Evaluated on {n} results so far.'.format(n=i))
        # Pre-processing: add batch dimension and convert to float32 to match with
        # the model's input data format.

        # load image by path
        loaded_img = keras.preprocessing.image.load_img(
            test_image, target_size=IMAGE_PAIR_SIZE, color_mode="grayscale"
        )
        img_array = keras.preprocessing.image.img_to_array(loaded_img)
        img_array = img_array.astype('float32')

        if floating_model:
            # Normalize to [0, 1]
            image_frame = img_array / 255.0
            images_data = np.expand_dims(image_frame, 0).astype(np.float32)  # or [img_data]
        else:  # 0.00390625 * q
            images_data = np.expand_dims(img_array, 0).astype(np.uint8)  # or [img_data]
        interpreter.set_tensor(input_index, images_data)

        # Run inference.
        interpreter.invoke()

        # Post-processing: remove batch dimension and find the digit with highest
        # probability.
        output = interpreter.tensor(output_index)
        pred_confidence = np.argmax(output()[0])

        is_mouth_opened = True if pred_confidence >= 0.2 else False
        # classes taken from input data
        predicted_label_id = class_indices['opened' if is_mouth_opened else 'closed']
        prediction_confs.append(predicted_label_id)

    print('\n')
    # Compare prediction results with ground truth labels to calculate accuracy.
    prediction_confs = np.array(prediction_confs)
    accuracy = (prediction_confs == test_labels).mean()
    return accuracy


def prune_model(model, train_generator, batch_size: int, valid_generator, output_keras_prune):
    import tensorflow_model_optimization as tfmot

    prune_low_magnitude = tfmot.sparsity.keras.prune_low_magnitude
    # Compute end step to finish pruning after 10 epochs.
    epochs = 10
    num_images = len(train_generator.filenames)
    end_step = np.ceil(num_images / (1.0 * batch_size)).astype(np.int32) * epochs

    # Define model for pruning.
    pruning_params = {
        'pruning_schedule': tfmot.sparsity.keras.PolynomialDecay(initial_sparsity=0.50,
                                                                 final_sparsity=0.80,
                                                                 begin_step=0,
                                                                 end_step=end_step)
    }

    model_for_pruning = prune_low_magnitude(model, **pruning_params)

    # `prune_low_magnitude` requires a recompile.
    model_for_pruning.compile(optimizer='adam',
                              loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                              metrics=['accuracy'])
    model_for_pruning.summary()

    logdir = tempfile.mkdtemp()
    callbacks = [
        tfmot.sparsity.keras.UpdatePruningStep(),
        tfmot.sparsity.keras.PruningSummaries(log_dir=logdir),
    ]
    model_for_pruning.fit(train_generator,
                          epochs=epochs,
                          batch_size=batch_size,
                          verbose=1,
                          validation_data=valid_generator,
                          callbacks=callbacks)

    _, model_for_pruning_accuracy = model_for_pruning.evaluate(
        valid_generator, verbose=1)
    # print('Baseline test accuracy:', baseline_model_accuracy)
    print('Pruned test accuracy:', model_for_pruning_accuracy)

    model_for_export = tfmot.sparsity.keras.strip_pruning(model_for_pruning)
    tf.keras.models.save_model(model_for_export, output_keras_prune, include_optimizer=False)
    print('Saved pruned Keras model to:', output_keras_prune)


def export_tf_js(model, path: str):
    try:
        import tensorflowjs as tfjs
    except ImportError:
        tfjs = None
    if tfjs:
        tfjs.converters.save_keras_model(model, path)
        print('Saved TFJS model to:', path)
    else:
        print("You could convert tfjs right now, if you had tensorflowjs module.")


def convert_tf2onnx(saved_model, onnx_path):
    # Convert keras to onnx
    # import keras2onnx
    # keras_model = keras.models.load_model(KERAS_MODEL_PATH)
    # onnx_model = keras2onnx.convert_keras(keras_model, ONNX_MODEL_PATH)

    # https://github.com/ysh329/deep-learning-model-convertor
    cmd = f"python -m tf2onnx.convert --saved-model {saved_model} --output {onnx_path}"
    if os.system(cmd) == 0:
        print('Saved onnx model', onnx_path)
    else:
        print('Failed to convert saved model to onnx', saved_model)


def export_pb(saved_model, output_path, input_shape):
    from tensorflow.python.framework.convert_to_constants import convert_variables_to_constants_v2
    model = tf.saved_model.load(saved_model)
    full_model = tf.function(lambda x: model(x))
    f = full_model.get_concrete_function(
        tf.TensorSpec(shape=input_shape,
                      dtype=tf.float32))
    f2 = convert_variables_to_constants_v2(f)
    graph_def = f2.graph.as_graph_def()
    # Export frozen graph
    with tf.io.gfile.GFile(output_path, 'wb') as f:
        f.write(graph_def.SerializeToString())
    print('Saved frozen model to:', output_path)


def export_tflite_floating2(output_model: str, saved_model: str, shape):
    model = tf.saved_model.load(saved_model)
    concrete_func = model.signatures[
        tf.saved_model.DEFAULT_SERVING_SIGNATURE_DEF_KEY]
    # Specify the input shape
    concrete_func.inputs[0].set_shape(shape)
    # Convert the model and export
    converter = tf.lite.TFLiteConverter.from_concrete_functions([concrete_func])
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float16]  # Only for float16
    tflite_model = converter.convert()
    with open(output_model, "wb") as w:
        w.write(tflite_model)
    print('Saved TFLite floating16 to:', output_model)


def export_tflite_floating(output_model: str, saved_model: str):
    converter = tf.lite.TFLiteConverter.from_saved_model(saved_model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float16]
    tflite_float_model = converter.convert()
    with open(output_model, "wb") as w:
        w.write(tflite_float_model)
    print('Saved floating TFLite model to:', output_model)


def export_tflite_quant(output_model: str, saved_model: str):
    converter = tf.lite.TFLiteConverter.from_saved_model(saved_model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_quant_model = converter.convert()
    with open(output_model, "wb") as w:
        w.write(tflite_quant_model)
    print('Saved quantized TFLite model to:', output_model)


def evaluate_tflite_quant(quant_path, test_images, test_labels):
    # test tflite quality
    print('Evaluate quant TFLite model')
    interpreter_quant = tf.lite.Interpreter(model_path=quant_path)
    interpreter_quant.allocate_tensors()
    test_accuracy_tflite_q = evaluate_model(interpreter_quant, test_images, test_labels)
    print('Quantized TFLite test_accuracy:', test_accuracy_tflite_q)


def evaluate_tflite_float(float_path, test_images, test_labels):
    # test tflite quality
    print('Evaluate float TFLite model')
    interpreter_float = tf.lite.Interpreter(model_path=float_path)
    interpreter_float.allocate_tensors()
    test_accuracy_tflite_f = evaluate_model(interpreter_float, test_images, test_labels)
    print('Floating TFLite test_accuracy:', test_accuracy_tflite_f)


def listdir_nohidden(path):
    for f in os.listdir(path):
        if not f.startswith('.'):
            yield f


def listdir_fullpath(d):
    return [os.path.join(d, f) for f in list(listdir_nohidden(d))]


def predict_random_test_img(model, path: str, class_name: str, grayscale: bool):
    opened_mouth_img = os.path.join(path, class_name)
    open_img_paths = listdir_fullpath(opened_mouth_img)
    random_img = random.choice(open_img_paths)
    img = mpimg.imread(random_img)
    plt.imshow(img, cmap="gray" if grayscale else None)
    plt.show()
    predict_image(model, random_img, grayscale)


def show_img_preview(out_path_img: str, img_class_paths1, img_class_paths2, threshold, grayscale: bool):
    # Parameters for our graph; we'll output images in a 4x4 configuration
    nrows = 4
    ncols = 4
    # Index for iterating over images
    pic_index = 0
    # Set up matplotlib fig, and size it to fit 4x4 pics
    fig = plt.gcf()
    fig.set_size_inches(ncols * 4, nrows * 4)
    pic_index += 8
    next_eye_opened_pic = img_class_paths1[pic_index - 8:pic_index]
    next_closed_eye_pic = img_class_paths2[pic_index - 8:pic_index]
    for i, img_path in enumerate(next_eye_opened_pic + next_closed_eye_pic):
        # Set up subplot; subplot indices start at 1
        sp = plt.subplot(nrows, ncols, i + 1)
        # sp.axis('Off')  # Don't show axes (or gridlines)
        plt.grid(False)
        plt.xticks([])
        plt.yticks([])

        conf = get_conf_from_path(img_path)
        img_filename = os.path.basename(img_path)
        is_opened = "opened" if conf >= threshold else "closed"

        img = mpimg.imread(img_path)
        plt.xlabel("{} ({})".format(img_filename, is_opened, color='blue'))
        plt.imshow(img, cmap="gray" if grayscale else None)
    plt.savefig(out_path_img)
    plt.show()


def plot_freq_imgs(out_path_img: str, opened_eye_img_paths: list, closed_eye_img_paths: list):
    opened_freq = []
    closed_freq = []
    for image_path in opened_eye_img_paths:
        conf = get_conf_from_path(image_path)
        opened_freq.append(conf)
    for image_path in closed_eye_img_paths:
        conf = get_conf_from_path(image_path)
        closed_freq.append(conf)

    bins = numpy.linspace(0.0, 1.0, 50)
    plt.hist(closed_freq, bins=bins, label=f'Closed ({len(closed_eye_img_paths)})', color='blue', edgecolor='black')
    plt.hist(opened_freq, bins=bins, label=f'Opened ({len(opened_eye_img_paths)})', color='red', edgecolor='black')
    plt.legend(loc='upper right')
    plt.gca().set(title='Frequency Histogram', ylabel='Frequency')
    plt.xlim(0.0, 1.0)
    plt.legend()
    plt.xlabel('Open probability')
    plt.ylabel('Frequency')
    plt.savefig(out_path_img)
    plt.show()


def get_conf_from_path(img_path: str) -> float:
    if 'mouth' in img_path:  # if mouth classification
        img_filename = os.path.basename(img_path)
        filename_only = os.path.splitext(img_filename)[0]
        img_threshold = filename_only.split("_")
        if len(img_threshold) > 1:
            return float(img_threshold[1])

    # default branch - eyes
    import pathlib
    path = pathlib.PurePath(img_path)
    bottom_folder = path.parent.name
    return 1.0 if bottom_folder == 'opened' else 0.0


def plot_roc(out_path_img: str, y_true, y_score):
    fpr, tpr, _ = roc_curve(y_true, y_score)
    roc_auc = auc(fpr, tpr)
    plt.figure()
    lw = 2
    plt.plot(fpr, tpr, color='darkorange',
             lw=lw, label='ROC curve (area = %0.2f)' % roc_auc)
    plt.plot([0, 1], [0, 1], color='navy', lw=lw, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic')
    plt.legend(loc="lower right")
    plt.savefig(out_path_img)
    plt.show()
