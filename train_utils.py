import tempfile

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

# https://medium.com/edureka/tensorflow-image-classification-19b63b7bfd95
# https://www.tensorflow.org/hub/tutorials/tf2_text_classification
# https://keras.io/examples/vision/image_classification_from_scratch/
# https://www.kaggle.com/darthmanav/dog-vs-cat-classification-using-cnn
# Input Layer: It represent input image data. It will reshape image into single diminsion array. Example your image is 100x100=10000, it will convert to (100,1) array.
# Conv Layer: This layer will extract features from image.
# Pooling Layer: This layer reduces the spatial volume of input image after convolution.
# Fully Connected Layer: It connect the network from a layer to another layer
# Output Layer: It is the predicted values layer.


# plot diagnostic learning curves
from yawn_train.model_config import IMAGE_PAIR_SIZE


def summarize_diagnostics(history_dict, output_folder):
    acc = history_dict['accuracy']
    val_acc = history_dict['val_accuracy']
    loss = history_dict['loss']
    val_loss = history_dict['val_loss']

    epochs = range(1, len(acc) + 1)

    # Plot Epochs / Training and validation loss
    # "bo" is for "blue dot"
    plt.plot(epochs, loss, 'bo', label='Training loss')
    # b is for "solid blue line"
    plt.plot(epochs, val_loss, 'b', label='Validation loss')
    plt.title('Training and validation loss (Cross Entropy Loss)')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()
    plt.savefig(f"{output_folder}/plot_epochs_loss.png")
    plt.show()

    # Plot Epochs / Training and validation accuracy
    plt.clf()  # clear figure

    plt.plot(epochs, acc, 'bo', label='Training acc')
    plt.plot(epochs, val_acc, 'b', label='Validation acc')
    plt.title('Training and validation accuracy (Classification Accuracy)')
    plt.xlabel('Epochs')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.savefig(f"{output_folder}/plot_epochs_accuracy.png")
    plt.show()


def create_model(input_shape) -> keras.Model:
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
    opt = keras.optimizers.SGD(lr=0.001, momentum=0.9)
    model.compile(optimizer=opt, loss='binary_crossentropy', metrics=['accuracy'])
    return model


def create_model_old(input_shape, num_classes) -> keras.Model:
    # Let's then add a Flatten layer that flattens the input image, which then feeds into the next layer, a Dense layer, or fully-connected layer, with 128 hidden units. Finally, because our goal is to perform binary classification, our final layer will be a sigmoid, so that the output of our network will be a single scalar between 0 and 1, encoding the probability that the current image is of class 1 (class 1 being grass and class 0 being dandelion).
    # model = tf.keras.models.Sequential([tf.keras.layers.Flatten(input_shape=(IMAGE_SIZE, IMAGE_SIZE, 1)),
    #                                   tf.keras.layers.Dense(128, activation=tf.nn.relu),
    #                                  tf.keras.layers.Dense(1, activation=tf.nn.sigmoid)])
    data_augmentation = keras.Sequential(
        [
            layers.experimental.preprocessing.RandomFlip("horizontal"),
            layers.experimental.preprocessing.RandomRotation(0.1),
        ]
    )
    inputs = keras.Input(shape=input_shape)
    x = data_augmentation(inputs)
    # Entry block
    x = layers.experimental.preprocessing.Rescaling(1.0 / 255)(x)
    x = layers.Conv2D(32, 3, strides=2, padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation("relu")(x)

    x = layers.Conv2D(64, 3, padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation("relu")(x)

    previous_block_activation = x  # Set aside residual

    for size in [128, 256, 512, 728]:
        x = layers.Activation("relu")(x)
        x = layers.SeparableConv2D(size, 3, padding="same")(x)
        x = layers.BatchNormalization()(x)

        x = layers.Activation("relu")(x)
        x = layers.SeparableConv2D(size, 3, padding="same")(x)
        x = layers.BatchNormalization()(x)

        x = layers.MaxPooling2D(3, strides=2, padding="same")(x)

        # Project residual
        residual = layers.Conv2D(size, 1, strides=2, padding="same")(
            previous_block_activation
        )
        x = layers.add([x, residual])  # Add back residual
        previous_block_activation = x  # Set aside next residual

    x = layers.SeparableConv2D(1024, 3, padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation("relu")(x)

    x = layers.GlobalAveragePooling2D()(x)
    if num_classes == 2:
        activation = "sigmoid"
        units = 1
    else:
        activation = "softmax"
        units = num_classes

    x = layers.Dropout(0.5)(x)
    outputs = layers.Dense(units, activation=activation)(x)
    model = keras.Model(inputs, outputs)

    # configure the specifications for model training. We will train our model with the binary_crossentropy loss. We will use the Adam optimizer. Adam is a sensible optimization algorithm because it automates learning-rate tuning for us
    model.compile(optimizer=tf.optimizers.Adam(),
                  loss='binary_crossentropy',
                  metrics=['accuracy'])  # , 'mse', 'mae', 'mape'])
    return model


def evaluate_model(interpreter, test_images, test_labels):
    input_index = interpreter.get_input_details()[0]["index"]
    output_index = interpreter.get_output_details()[0]["index"]
    floating_model = interpreter.get_input_details()[0]['dtype'] == np.float32

    # Run predictions on ever y image in the "test" dataset.
    prediction_digits = []
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
        # prediction_digits.append(pred_confidence)

        is_mouth_opened = True if pred_confidence >= 0.2 else False
        # classes taken from input data
        class_indices = {'closed': 0, 'opened': 1}
        predicted_label_id = class_indices['opened' if is_mouth_opened else 'closed']
        prediction_digits.append(predicted_label_id)

    print('\n')
    # Compare prediction results with ground truth labels to calculate accuracy.
    prediction_digits = np.array(prediction_digits)
    accuracy = (prediction_digits == test_labels).mean()
    return accuracy


def prune_model(model, train_images, test_images, test_labels):
    import tensorflow_model_optimization as tfmot

    prune_low_magnitude = tfmot.sparsity.keras.prune_low_magnitude

    # Compute end step to finish pruning after 2 epochs.
    batch_size = 128
    epochs = 2
    validation_split = 0.1  # 10% of training set will be used for validation set.

    num_images = train_images.shape[0] * (1 - validation_split)
    end_step = np.ceil(num_images / batch_size).astype(np.int32) * epochs

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
    model_for_pruning.fit(train_images, train_labels,
                          batch_size=batch_size, epochs=epochs, validation_split=validation_split,
                          callbacks=callbacks)

    _, model_for_pruning_accuracy = model_for_pruning.evaluate(
        test_images, test_labels, verbose=0)
    print('Baseline test accuracy:', baseline_model_accuracy)
    print('Pruned test accuracy:', model_for_pruning_accuracy)
