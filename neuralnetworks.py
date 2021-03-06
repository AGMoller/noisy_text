"""
Classification using neural models.
Twitter Embeddings obtained from: https://nlp.stanford.edu/projects/glove/
"""

from myutils import Featurizer, EmbedsFeaturizer, get_size_tuple, PREFIX_WORD_NGRAM, PREFIX_CHAR_NGRAM, TWEET_DELIMITER

import random
import os
import argparse

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score
from scipy.sparse import hstack
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
import tensorflow as tf
from nltk.tokenize import word_tokenize
from tqdm import tqdm

from classify import encode_label, train_eval

# Fix seed for replicability
seed=103
random.seed(seed)
np.random.seed(seed)

def fileLoadPrep(file, embedding_file, word_tokenizer = False, length_median = False):
    """
    Load file and prepare data based on GloVe embeddings. 
    Tutorial followed: https://stackabuse.com/python-for-nlp-word-embeddings-for-deep-learning-in-keras/
    """
    # Load file
    df = pd.read_csv(file, sep="\t")
    df["Label"] = df["Label"].apply(lambda x: encode_label(x))
    
    y = df["Label"]

    if word_tokenizer == False:
        # Define and fit word tokenizer
        word_tokenizer = tf.keras.preprocessing.text.Tokenizer()
        word_tokenizer.fit_on_texts(df["Text"].values)
        embedded_sentences = word_tokenizer.texts_to_sequences(df["Text"].values)
    else:
    # Embed sentences
        embedded_sentences = word_tokenizer.texts_to_sequences(df["Text"].values)

    # Vocab length
    vocab_length = len(word_tokenizer.word_index) + 1

    # Find max/mean/median tweet length
    if length_median == False:
        word_count = lambda sentence: len(word_tokenize(sentence))
        length_median = int(np.median([word_count(i) for i in df["Text"].values]))

    # Pad sentences
    X = tf.keras.preprocessing.sequence.pad_sequences(embedded_sentences, length_median, padding='post')

    # Prepare embeddings
    embeddings_dictionary = dict()
    glove_file = open(embedding_file, encoding="utf8")
    for line in tqdm(glove_file):
        records = line.split()
        word = records[0]
        vector_dimensions = np.asarray(records[1:], dtype='float32')
        embeddings_dictionary [word] = vector_dimensions
    glove_file.close()

    embedding_matrix = np.zeros((vocab_length, 200))
    for word, index in word_tokenizer.word_index.items():
        embedding_vector = embeddings_dictionary.get(word)
        if embedding_vector is not None:
            embedding_matrix[index] = embedding_vector

    print("Done")

    return X, y, embedding_matrix, vocab_length, length_median, word_tokenizer


def makeModel(vocab_length, embedding_dim, embedding_matrix, input_dim):
    
    ##############################
    ####### For FFNN model #######
    ##############################
    model = tf.keras.Sequential()
    embedding_layer = tf.keras.layers.Embedding(vocab_length, embedding_dim, weights=[embedding_matrix], input_length=input_dim, trainable=False)
    model.add(embedding_layer)
    model.add(tf.keras.layers.Dense(1024, activation="relu"))
    model.add(tf.keras.layers.Dropout(0.5))
    model.add(tf.keras.layers.Dense(512, activation = "relu"))
    model.add(tf.keras.layers.Flatten())
    model.add(tf.keras.layers.Dense(1, activation='sigmoid'))

    ################################
    ####### For Conv1d model #######
    ################################
    # embedding_layer = tf.keras.layers.Embedding(vocab_length, embedding_dim, weights=[embedding_matrix], input_length=input_dim, trainable=False)
    # model.add(embedding_layer)
    # model.add(tf.keras.layers.Conv1D(filters = 64, kernel_size = 5, activation="relu"))
    # model.add(tf.keras.layers.Dropout(0.5))
    # model.add(tf.keras.layers.MaxPooling1D(pool_size=2))
    # model.add(tf.keras.layers.Flatten())
    # model.add(tf.keras.layers.Dense(1, activation='sigmoid'))

    model.compile(optimizer='adagrad', loss='binary_crossentropy', metrics=['acc'])

    return model

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--embedFile", required=True, help = "Specify embedding file")
    #parser.add_argument()
    args = parser.parse_args()

    train_data_path = "data/train_lower_entities.tsv"
    test_data_path = "data/valid_lower_entities.tsv"
    embedding_file = args.embedFile

    X_train, y_train, embedding_matrix, vocab_length, input_dim, word_tokenizer = fileLoadPrep(train_data_path, embedding_file)
    print("Training loaded")

    X_test, y_test, _, _, _, _ = fileLoadPrep(test_data_path, embedding_file, word_tokenizer, input_dim)
    print("Test loaded")

    model = makeModel(vocab_length, embedding_matrix.shape[1], embedding_matrix, input_dim)
    print("Model made")

    model.fit(X_train, y_train, epochs=50, verbose=1)
    print("Training done")

    preds = model.predict(X_test)
    np.save("MLP_preds_proba.npy",preds)
    preds = np.array([0 if i < 0.5 else 1 for i in preds])
    np.save("MLP_preds.npy",preds)
    #print(preds[:20])

    loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
    print('Accuracy: %f' % (accuracy*100))