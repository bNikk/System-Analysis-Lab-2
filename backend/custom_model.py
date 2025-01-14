import numpy as np
import matplotlib.pyplot as plt
from copy import deepcopy
from tqdm import tqdm
from backend.utils import *


class CustomModel:

    def __init__(self, dataset_size, x_path, y_path, x_size, y_size, b_type, polynom_type, polynom_degrees,
                 polynom_search, lambda_type, output_file):
        self.dataset_size = dataset_size
        self.x = np.loadtxt(x_path)
        self.y = np.loadtxt(y_path)
        self.y = self.y.reshape(self.y.shape[0], -1)
        self.x_size = x_size
        self.y_size = y_size
        self.y = self.y[:, :self.y_size]

        if polynom_type == 'chebyshev':
            self.polynom_function = eval_chebyt
        elif polynom_type == 'hermit':
            self.polynom_function = eval_hermite
        elif polynom_type == 'legendre':
            self.polynom_function = eval_legendre
        elif polynom_type == 'laguerre':
            self.polynom_function = eval_laguerre
        elif polynom_type == 'u':
            self.polynom_function = eval_u
        elif polynom_type == 'c':
            self.polynom_function = eval_c
        elif polynom_type == 's':
            self.polynom_function = eval_s
        elif polynom_type == 'custom':
            self.polynom_function = eval_custom

        self.polynom_type = polynom_type
        self.b_type = b_type
        self.polynom_search = polynom_search
        if not self.polynom_search:
            self.polynom_degrees = polynom_degrees
        self.lambda_type = lambda_type
        self.output_file = output_file

        self.cache_y = None
        self.cache_min_max = None
        self.b = None
        self.coef_lambda = None
        self.coef_a = None
        self.coef_c = None
        self.X_coef_lambda = None
        self.X_coef_a = None
        self.X_coef_c = None

    def norm(self):
        self.cache_min_max = dict()
        for index in range(self.x.shape[1]):
            key = 'x' + str(index)
            self.cache_min_max[key] = [self.x[:, index].min(), self.x[:, index].max()]
            self.x[:, index] = (self.x[:, index] - self.cache_min_max[key][0]) / (
                    self.cache_min_max[key][1] - self.cache_min_max[key][0])

        self.cache_y = deepcopy(self.y)
        for index in range(self.y.shape[1]):
            key = 'y' + str(index)
            self.cache_min_max[key] = [self.y[:, index].min(), self.y[:, index].max()]
            self.y[:, index] = (self.y[:, index] - self.cache_min_max[key][0]) / (
                    self.cache_min_max[key][1] - self.cache_min_max[key][0])

    def set_b(self):
        if self.b_type == 'norm':
            self.b = deepcopy(self.y)
        elif self.b_type == 'mean':
            self.b = np.zeros((self.y.shape[0], 1))
            for i in range(self.y.shape[0]):
                self.b[i, :] = (np.max(self.y[i, :self.y_size]) + np.min(self.y[i, :self.y_size])) / 2

    def evaluate_degrees(self, degrees):
        b_mean = np.mean(self.b, axis=1)
        # Multiply
        b_mean = np.log(b_mean + 1)
        new_shape_X = (self.x.shape[0], np.sum((np.array(degrees) + 1) * np.array(self.x_size)))
        X = np.zeros(new_shape_X)
        pointer_X = 0
        pointer_x = 0
        for i in range(3):
            for _ in range(self.x_size[i]):
                for d in range(degrees[i] + 1):
                    # Multiply
                    #print(1 + self.polynom_function(d, self.x[:, pointer_x]) + 1e-9)
                    X[:, pointer_X] = np.log(np.abs(1 + self.polynom_function(d, self.x[:, pointer_x]) + 1e-9))
                    X[:, pointer_X] += np.log(1 + np.cos(self.polynom_function(d, self.x[:, pointer_x])))
                    pointer_X += 1
                pointer_x += 1
        score = np.abs((b_mean - np.dot(X, get_coef(X, b_mean)))).mean()
        return score

    def find_polynom_degrees(self):
        degrees = [1, 1, 1]
        for index in tqdm(range(3)):
            best_score = np.inf
            best_degree = 1
            for degree in range(1, 11):
                degrees[index] = degree
                score = self.evaluate_degrees(degrees)
                if score < best_score:
                    best_score = score
                    best_degree = degree
            degrees[index] = best_degree
        print(degrees, best_score)
        self.polynom_degrees = degrees

    def find_coef_lambda_all(self):
        b_mean = np.mean(self.b, axis=1)
        # Multiply
        b_mean = np.log(b_mean + 1)
        new_shape_X = (self.x.shape[0], np.sum((np.array(self.polynom_degrees) + 1) * np.array(self.x_size)))
        X = np.zeros(new_shape_X)
        pointer_X = 0
        pointer_x = 0
        for i in range(3):
            for _ in range(self.x_size[i]):
                for d in range(self.polynom_degrees[i] + 1):
                    # Multiply
                    X[:, pointer_X] = np.log(np.abs(1 + self.polynom_function(d, self.x[:, pointer_x]) + 1e-9))
                    X[:, pointer_X] += np.log(1 + np.cos(self.polynom_function(d, self.x[:, pointer_x])))
                    pointer_X += 1
                pointer_x += 1
        self.coef_lambda = get_coef(X, b_mean)
        self.X_coef_lambda = X

    def find_coef_lambda_separately(self):
        b_mean = np.mean(self.b, axis=1)
        # Multiply
        b_mean = np.log(b_mean + 1)
        coef_lambda = []
        X_coef_lambda = []
        pointer_x = 0
        for i in range(3):
            tmp_X = np.zeros((self.x.shape[0], (self.polynom_degrees[i] + 1) * self.x_size[i]))
            pointer_X = 0
            for _ in range(self.x_size[i]):
                for d in range(self.polynom_degrees[i] + 1):
                    # Multiply
                    tmp_X[:, pointer_X] = np.log(np.abs(1 + self.polynom_function(d, self.x[:, pointer_x]) + 1e-9))
                    tmp_X[:, pointer_X] += np.log(1 + np.cos(self.polynom_function(d, self.x[:, pointer_x])))
                    pointer_X += 1
                pointer_x += 1
            tmp_coef_lambda = get_coef(tmp_X, b_mean)
            coef_lambda.append(tmp_coef_lambda)
            X_coef_lambda.append(tmp_X)

        self.X_coef_lambda = np.concatenate(X_coef_lambda, axis=1)
        self.coef_lambda = np.concatenate(coef_lambda, axis=0)

    def find_coef_a(self):
        coef_a = dict()
        X_coef_a = dict()
        for index in range(self.y_size):
            tmp_y = self.y[:, index]
            # Multiply
            tmp_y = np.log(1 + tmp_y)
            coef_a[index] = []
            X_coef_a[index] = []
            pointer = 0
            for i in range(3):
                tmp_X = np.zeros((self.X_coef_lambda.shape[0], self.x_size[i]))
                for j in range(self.x_size[i]):
                    polynom_subset = self.X_coef_lambda[:, pointer:pointer + self.polynom_degrees[i] + 1]
                    lambda_coef_subset = self.coef_lambda[pointer:pointer + self.polynom_degrees[i] + 1]
                    tmp_X[:, j] = np.dot(polynom_subset, lambda_coef_subset)
                    tmp_X[:, j] += np.log(1 + 0.001 * np.cos(np.exp(tmp_X[:, j]) - 1))
                    pointer += self.polynom_degrees[i] + 1
                tmp_coef_a = get_coef(tmp_X, tmp_y)

                X_coef_a[index].append(tmp_X)
                coef_a[index].append(tmp_coef_a)

        self.coef_a = coef_a
        self.X_coef_a = X_coef_a

    def find_coef_c(self):
        coef_c = dict()
        X_coef_c = dict()
        for index in range(self.y_size):
            tmp_y = self.y[:, index]
            # Multiply
            tmp_y = np.log(1 + tmp_y)
            tmp_X = np.zeros((self.X_coef_lambda.shape[0], 3))
            for i in range(3):
                tmp_X[:, i] = np.dot(self.X_coef_a[index][i], self.coef_a[index][i])
            tmp_coef_c = get_coef(tmp_X, tmp_y)
            X_coef_c[index] = tmp_X
            coef_c[index] = tmp_coef_c

        self.X_coef_c = X_coef_c
        self.coef_c = coef_c

    def find_additive_model(self):
        self.norm()
        self.set_b()

        if self.polynom_search:
            self.find_polynom_degrees()

        if self.lambda_type == 'all':
            self.find_coef_lambda_all()
        elif self.lambda_type == 'separately':
            self.find_coef_lambda_separately()

        self.find_coef_a()
        self.find_coef_c()

    def get_coef_lambda(self):
        string = f'Коефіцієнти \u03BB \n'
        pointer = 0
        for i in range(3):
            for j in range(self.x_size[i]):
                for d in range(self.polynom_degrees[i] + 1):
                    coef = self.coef_lambda[pointer]
                    string += f'\u03BB{i + 1}{j + 1}{d}={coef:.4f}  '
                    pointer += 1
                string += '\n'
        return string

    def get_coef_a(self):
        string = 'Коефіцієнти а \n'
        for index in range(self.y_size):
            string += f'i = {index + 1} \n'
            for i, coef in enumerate(self.coef_a[index]):
                for j in range(len(coef)):
                    string += f'a{i + 1}{j + 1}={coef[j]:.4f} '
                string += '\n'
        return string

    def get_coef_c(self):
        string = 'Коефіцієнти с \n'
        for index in range(self.y_size):
            string += f'i = {index + 1} \n'
            for j in range(len(self.coef_c[index])):
                string += f'c{j + 1}={self.coef_c[index][j]:.4f} '
            string += '\n'
        return string

    def get_function_theta(self):
        string = 'Функції \u03A8 \n'
        pointer = 0
        for i in range(3):
            for j in range(self.x_size[i]):
                string += f'\u03A8{i + 1}{j + 1}(x{i + 1}{j + 1}) = '
                for d in range(self.polynom_degrees[i] + 1):
                    coef = self.coef_lambda[pointer]
                    string += f'(1 + \u03c6{d}(x{i + 1}{j + 1}))^{coef:.4f}'
                    pointer += 1
                    if d != self.polynom_degrees[i]:
                        string += ' *  '
                string += ' - 1 \n'

        return string

    def get_function_f_i(self):
        string = 'Функції Ф_ij \n'
        for index in range(self.y_size):
            for i, coef in enumerate(self.coef_a[index]):
                string += f'Ф{index + 1}{i + 1}(x{i + 1})= '
                for j in range(len(coef)):
                    string += f'(1 + \u03A8{i + 1}{j + 1}(x{i + 1}{j + 1}))^{coef[j]:.4f}'
                    if j != len(coef) - 1:
                        string += ' *  '
                string += ' - 1 \n'
        return string

    def get_final_approximation_f(self):
        string = 'Одержані функції через Ф \n'
        for index in range(self.y_size):
            string += f'Ф{index + 1}(x1, x2, x3) = '
            for j in range(len(self.coef_c[index])):
                string += f'(1 + Ф{index + 1}{j + 1}(x{j + 1}))^{self.coef_c[index][j]:.4f}'
                if j != len(self.coef_c[index]) - 1:
                    string += ' *  '
            string += ' - 1 \n'
        return string

    def get_final_approximation_polynoms_denorm(self):
        string = 'Одержані функції через Ф у відтвореному вигляді\n'
        for index in range(self.y_size):
            key = f'y{index}'
            string += f'Ф{index + 1}(x1, x2, x3) = {(self.cache_min_max[key][1] - self.cache_min_max[key][0]):.4f} * '
            for j in range(len(self.coef_c[index])):
                string += f'(1 + Ф{index + 1}{j + 1}(x{j + 1}))^{self.coef_c[index][j]:.4f}'
                if j != len(self.coef_c[index]) - 1:
                    string += ' *  '
            string += f' + {self.cache_min_max[key][0] - 1} \n'
        return string

    def write_in_file(self):
        with open(self.output_file, 'w') as file:
            if self.polynom_search:
                file.write(f'Найкращі степені поліномів : '
                           f'{self.polynom_degrees[0]} {self.polynom_degrees[1]} {self.polynom_degrees[2]} \n\n')
            # file.write(self.get_coef_lambda() + '\n')
            # file.write(self.get_coef_a() + '\n')
            # file.write(self.get_coef_c() + '\n')
            file.write(self.get_function_theta() + '\n')
            file.write(self.get_function_f_i() + '\n')
            file.write(self.get_final_approximation_f() + '\n')
            file.write(self.get_final_approximation_polynoms_denorm())

        with open(self.output_file, 'r') as file:
            content_to_print = file.read()

        return content_to_print

    def get_plot(self, y_number=1, norm=True):
        ground_truth = self.y[:, y_number - 1]
        predict = np.exp(np.dot(self.X_coef_c[y_number - 1], self.coef_c[y_number - 1])) - 1
        if not norm:
            y_min, y_max = self.cache_min_max[f'y{y_number - 1}']
            ground_truth = ground_truth * (y_max - y_min) + y_min
            predict = predict * (y_max - y_min) + y_min
        error = np.mean(np.abs(predict - ground_truth))
        plt.title(f'Відновлена функціональна залежність для Y{y_number} з похибкою {error:.6f}')
        plt.plot(np.arange(1, len(ground_truth) + 1),
                 ground_truth,
                 label=f'Y{y_number}')
        plt.plot(np.arange(1, len(ground_truth) + 1),
                 predict,
                 label='Ф11 + Ф12 + Ф13',
                 linestyle='--')
        plt.legend()
        plt.show()