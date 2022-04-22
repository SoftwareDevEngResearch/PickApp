# @Time : 4/7/2022 11:15 AM
# @Author : Alejandro Velasquez

from sklearn.utils import resample

import os
import numpy as np
from numpy import genfromtxt
import math
import statistics as st
import matplotlib.pyplot as plt
from statistics import mean, stdev
import pandas as pd
from tqdm import tqdm
import csv


def check_size(source):

    lowest = 10000
    highest = 0
    sizes = []
    for filename in tqdm(os.listdir(source)):

        data = pd.read_csv(source + filename)
        n_samples = data.shape[0]
        sizes.append(n_samples)

        if n_samples < lowest:
            lowest = n_samples

        if n_samples > highest:
            highest = n_samples

    title = "Lowest= " + str(lowest) + " / Highest= " + str(highest) + " / Mean=" + str(round(mean(sizes),2)) + " / SD= " + str(round(stdev(sizes),2))
    plt.title(title)
    plt.boxplot(sizes)
    plt.show()

    return lowest, highest


def down_sample(period, source, target):
    """
    Downsamples all the csv files located in source folder, and saves the new csv in target folder
    :param period: period [ms] at which you want to sample the time series
    :param source:
    :param target:
    :return:
    """

    for filename in tqdm(os.listdir(source)):
        # print(filename)

        # --- Step 0: Read csv data into a a Pandas Dataframe ---
        # Do not include the first column that has the time, so we don't overfit the next processes
        # data = genfromtxt((source + filename), delimiter=',', skip_header=True)

        data = pd.read_csv(source + filename)
        n_samples = data.shape[0]       # rows
        n_channels = data.shape[1]      # columns

        max_time = data.iloc[-1, 0]

        # Create New Dataframe
        downsampled_data = pd.DataFrame()
        headers = pd.read_csv(source + filename, index_col=0, nrows=0).columns.tolist()

        # print(headers)

        for i in range(n_channels):
            new_value = []
            if i == 0:
                # --- Time Channel
                new_time = []

                time = data.iloc[0, 0]
                while time < max_time:
                    new_time.append(time)
                    time = time + period/1000
                    # print(time)
                header = "Time"
                downsampled_data[header] = new_time

            else:
                # --- The rest of the channels
                new_value = []
                index = 0
                for x in new_time:
                    for k in data.iloc[index:, 0]:
                        if k > x:
                            break
                        else:
                            index += 1

                    # Interpolation
                    x1 = data.iloc[index-1, 0]
                    x2 = data.iloc[index, 0]
                    y1 = data.iloc[index-1, i]
                    y2 = data.iloc[index, i]
                    value = (y1 - y2)*(x2 - x)/(x2 - x1) + y2
                    new_value.append(value)

                    header = headers[i-1]

                downsampled_data[header] = new_value

                # --- Compare PLots ---
                # plt.plot(data.iloc[:, 0], data.iloc[:, i])
                # plt.plot(new_time, new_value)
                # plt.show()

        # print(downsampled_data)
        downsampled_data.to_csv(target + filename, index=False)


def join_csv(name, case, source, target):
    """
    Joins csv from different topics but from the same experiment, into a single csv.
    Thus, data is easier to handle, and less prone to make mistakes.
    It does some cropping of the initial or last points, in order to have all the topics have the same size
    :param name: Name of the experiment
    :param case: Whether Grasp or Pick stage
    :param source:
    :param target:
    :return:
    """

    if case == 'GRASP/':
        stage = 'grasp'
    elif case == 'PICK/':
        stage = 'pick'

    # --- Step 1: Open all the topics from the same experiment that need to be joined ---
    location = source
    topics = ['_wrench', '_f1_imu', '_f1_states', '_f2_imu', '_f2_states', '_f3_imu', '_f3_states']

    data_0 = pd.read_csv(location + name + stage + topics[0] + '.csv', header=None, index_col=False)
    data_1 = pd.read_csv(location + name + stage + topics[1] + '.csv', header=None, index_col=False)
    data_2 = pd.read_csv(location + name + stage + topics[2] + '.csv', header=None, index_col=False)
    data_3 = pd.read_csv(location + name + stage + topics[3] + '.csv', header=None, index_col=False)
    data_4 = pd.read_csv(location + name + stage + topics[4] + '.csv', header=None, index_col=False)
    data_5 = pd.read_csv(location + name + stage + topics[5] + '.csv', header=None, index_col=False)
    data_6 = pd.read_csv(location + name + stage + topics[6] + '.csv', header=None, index_col=False)

    dataframes = [data_0, data_1, data_2, data_3, data_4, data_5, data_6]

    # --- Step 2: Crop initial or last points in order to make all topics have the same length
    # Get the channel with the less sampled points
    smallest = 10000
    for channel in dataframes:
        if channel.shape[0] < smallest:
            smallest = channel.shape[0]
            benchmark = channel
    # print("\nSmallest:", smallest)

    benchmark_first = float(benchmark.iloc[1, 0])  # First Reading
    benchmark_last = float(benchmark.iloc[-1, 0])  # Last Reading
    # print("First and last", benchmark_first, benchmark_last)

    count = 0
    for channel in dataframes:
        if channel.shape[0] > smallest:
            difference = channel.shape[0] - smallest
            print("The difference is", difference)

            # Check which points to crop, the initial or last ones
            initial_time_offset = abs(float(channel.iloc[1, 0]) - benchmark_first)
            last_time_offset = abs(float(channel.iloc[-1, 0]) - benchmark_last)

            if initial_time_offset > last_time_offset:
                print("Remove initial")
                for i in range(difference):
                    new_df = channel.drop([1]).reset_index(drop=True)
            else:
                print("Remove last")
                new_df = channel.iloc[:-difference, :]

            dataframes[count] = new_df

        count = count + 1

    # --- Step 3: Join them all into a single DataFrame and save
    df = pd.concat([dataframes[0].iloc[:, 1:], dataframes[1].iloc[:, 1:], dataframes[2].iloc[:, 1:],
                    dataframes[3].iloc[:, 1:], dataframes[4].iloc[:, 1:], dataframes[5].iloc[:, 1:],
                    dataframes[6].iloc[:, 1:]], axis=1)
    new_file_name = target + name + '_' + str(stage) + '.csv'
    df.to_csv(new_file_name, index=False, header=False)


def crop_csv(size, source, target):

    for filename in tqdm(os.listdir(source)):

        data = pd.read_csv(source + filename)
        n_samples = data.shape[0]
        difference = n_samples - size
        start = int(difference/2)
        end = start + size
        cropped_data = data.iloc[start:end, :]
        cropped_data.to_csv(target + filename, index=False)


def main():
    # Step 1 - Read Data saved as csvs from bagfiles
    # Step 2 - Split the data into Grasp and Pick
    # (pp) grasp_and_pick_split.py

    # Step 3 - Select the columns to pick
    # (pp) real_pick_delCol.py

    main = 'C:/Users/15416/Box/Learning to pick fruit/Apple Pick Data/RAL22 Paper/'
    dataset = '3_proxy_winter22_x1/'
    # dataset = '5_real_fall21_x1/'
    # dataset = '1_proxy_rob537_x1/'
    stages = ['GRASP/', 'PICK/']

    # (pp) downsampler.py
    for stage in tqdm(stages):
        location = main + dataset + stage
        location_1 = location + 'pp1_split/'
        location_2 = location + 'new_pp2_downsampled/'
        location_3 = location + 'new_pp3_joined/'
        location_4 = location + 'new_pp4_labeled/'

        # --- Step 4: Down sample Data ---
        period = 15  # Sampling period in [ms]
        # down_sample(period, location_1, location_2)

        # --- Step 5: Crop Data ---
        # l, h = check_size(location_2)
        # print(dataset, stage, l, h)
        if stage == 'GRASP/':
            size = 106
        elif stage == 'PICK/':
            size = 115
        # crop_csv(size, location_2, location_3)

    # --- Step 6: Join Data ---
    # Here we want to end up with a list the size of the medatadafiles
    # Thus makes sense to get the names from the metadata folder
    # (pp) csv_joiner.py
    metadata_loc = main + dataset + 'metadata/'

    for filename in tqdm(sorted(os.listdir(metadata_loc))):

        # Get the basic name
        name = str(filename)
        start = name.index('app')
        end = name.index('m')
        name = name[start:end]
        print(name)

        for stage in stages:
            print(stage)
            location = main + dataset + stage
            location_2 = location + 'new_pp2_downsampled/'
            location_3 = location + 'new_pp3_joined/'
            join_csv(name, stage, location_2, location_3)

    # --- Step 7: Augment Data ---

    # Step 6 - Do Data Augmentation by adding Noise
    # TODO

    # Step 7 - Save csvs in subfolders labeled
    # (pp) data_into_labeled_folder.py


if __name__ == '__main__':
    main()