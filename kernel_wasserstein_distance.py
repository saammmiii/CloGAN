from numpy.random import default_rng
from utils.welford import Welford
from datasets.cheXpert_dataset import read_dataset
from utils.visualization import *
from models.multi_label import *


GENERATE_FEATURE = True

if TRAIN_CHEXPERT:
    FEATURES_NP_FILE = "../records/chextpert_train_input_features"
else:
    FEATURES_NP_FILE = "../records/chestray14_train_input_features"

N_SAMPLES = 60


def calc_J(n):
    arrow_1 = np.ones(n)
    s = arrow_1[np.newaxis, :].T / n
    J = (np.identity(n) - s * arrow_1) / n ** .5
    return J


def calc_K(x: np.ndarray, y: np.ndarray):
    return x[np.newaxis, :].T * y


def calc_k(x: np.ndarray, y: np.ndarray, gamma=None):
    x_num_features = x.shape[-1]
    y_num_features = y.shape[-1]

    if gamma is None:
        gamma = 1.0

    x = np.repeat(x.T[:, np.newaxis], y_num_features, 1)
    y = np.repeat(y[np.newaxis, :], x_num_features, 0)
    _sum = np.exp(-gamma * (x - y) ** 2).sum()
    return _sum


def kernel_wasserstein_distance(u_values: np.ndarray, v_values: np.ndarray):
    # n & m
    n = u_values.size
    m = v_values.size

    J_1 = calc_J(n)
    J_2 = calc_J(m)

    W_2 = calc_k(u_values, u_values) / n ** 2 - calc_k(u_values, v_values) * 2 / (n * m) \
          + calc_k(v_values, v_values) / m ** 2 + np.trace(J_1 @ J_1.T @ calc_K(u_values, u_values)) \
          + np.trace(J_2 @ J_2.T @ calc_K(v_values, v_values)) \
          - 2 * np.trace(calc_K(u_values, v_values) @ J_2 @ J_2.T @ calc_K(v_values, u_values) @ J_1 @ J_1.T) ** .5

    return W_2



if __name__ == "__main__":
    # features1 = calc_glcm_features(read_resize_image("C:/Users/samue/Desktop/sample_dataset/chexpert/view1_frontal_3.jpg", NUM_LEVELS).numpy())
    # features2 = calc_glcm_features(read_resize_image("C:/Users/samue/Desktop/sample_dataset/chexpert/view1_frontal_1.jpg", NUM_LEVELS).numpy())
    # print(kernel_wasserstein_distance(features1, features2))

    if GENERATE_FEATURE:
        model = model_binaryXE_mid()
        model.load_weights("networks/chexpert.hdf5" if TRAIN_CHEXPERT else "networks/chestxray14.hdf5")

        # get the dataset
        train_dataset = read_dataset(
            CHEXPERT_TRAIN_TARGET_TFRECORD_PATH if TRAIN_CHEXPERT else CHESTXRAY_TRAIN_TARGET_TFRECORD_PATH,
            CHEXPERT_DATASET_PATH if TRAIN_CHEXPERT else CHESTXRAY_DATASET_PATH, shuffle=False)

        _train_n = TRAIN_N

        features_nps = np.zeros((_train_n, 2048))
        # get the ground truth labels
        for i_d, (test_img, _) in tqdm(enumerate(train_dataset), total=math.ceil(_train_n / BATCH_SIZE)):
            # Evaluate the model on the test data using `evaluate`
            features_nps[i_d*BATCH_SIZE: (i_d + 1)*BATCH_SIZE] = model.predict(test_img)[1]

        np.save(FEATURES_NP_FILE, features_nps)  # save it

    # load
    features_nps = np.load(FEATURES_NP_FILE + ".npy")

    # run kernel_wasserstein_distance
    rng = default_rng()
    sample_numbers = rng.choice(TRAIN_N, size=N_SAMPLES, replace=False)
    welford_ = Welford()

    for i in tqdm(sample_numbers):
        for j in range(TRAIN_N):
            if i == j: continue
            welford_(kernel_wasserstein_distance(features_nps[i], features_nps[j]))
        print(i, ":", welford_)

    print(welford_)
    print("k:", welford_.k)