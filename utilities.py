"""
Utilty and convenience functions for a number of QAOA applications.

See the demo notebook UtilitiesDemo.ipynb for exampels on usage of the methods herein.
"""

from typing import Union, List, Type, Dict, Iterable

import numpy as np
import pandas as pd
import networkx as nx

import matplotlib.pyplot as plt

from pyquil.quil import Program, Qubit, QubitPlaceholder, address_qubits
from pyquil.paulis import PauliSum, PauliTerm
from pyquil.gates import X
from scipy.spatial import distance

from sklearn.metrics import accuracy_score

### METHODS FOR CREATING HAMILTONIANS AND GRAPHS, AND SWITCHING BETWEEN THE TWO ###


def hamiltonian_from_hyperparams(nqubits: int,
                                 singles: List[int],
                                 biases: List[float],
                                 pairs: List[int],
                                 couplings: List[float]) -> PauliSum:
    """
    Builds a cost Hamiltonian as a PauliSum from a specified set of problem hyperparameters.

    Parameters
    ----------
    nqubits:
        The number of qubits.
    singles:
        The register indices of the qubits that have a bias term
    biases:
        Values of the biases on the qubits specified in singles.
    pairs:
        The qubit pairs that have a non-zero coupling coefficient.
    couplings:
        The value of the couplings for each pair of qubits in pairs.

    Returns
    -------
    Hamiltonian
        The PauliSum representation of the networkx graph.
    """

    hamiltonian = []
    for i in range(len(pairs)):
        hamiltonian.append(PauliTerm('Z', pairs[i][0], couplings[i]) * PauliTerm('Z', pairs[i][1]))

    for i in range(len(singles)):
        hamiltonian.append(PauliTerm('Z', singles[i], biases[i]))

    return PauliSum(hamiltonian)


def random_hamiltonian(nqubits: int) -> PauliSum:
    """
    Creates a random cost hamiltonian, diagonal in the computational basis:

     - Randomly selects which qubits that will have a bias term, then assigns them a bias coefficient.
     - Randomly selects which qubit pairs will have a coupling term, then assigns them a coupling coefficient.

     In both cases, the random coefficient is drawn from the uniform distribution on the interval [0,1).

    Parameters
    ----------
    nqubits:
        The desired number of qubits.

    Returns
    -------
    hamiltonian:
        A hamiltonian with random couplings and biases, as a PauliSum object.

    """
    hamiltonian = []

    numb_biases = np.random.randint(nqubits)
    bias_qubits = np.random.choice(nqubits, numb_biases, replace=False)
    bias_coeffs = np.random.rand(numb_biases)
    for i in range(numb_biases):
        hamiltonian.append(PauliTerm("Z", int(bias_qubits[i]), bias_coeffs[i]))

    for i in range(nqubits):
        for j in range(i + 1, nqubits):
            are_coupled = np.random.randint(2)
            if are_coupled:
                couple_coeff = np.random.rand()
                hamiltonian.append(PauliTerm("Z", i, couple_coeff) * PauliTerm("Z", j))

    return PauliSum(hamiltonian)


def graph_from_hamiltonian(hamiltonian: PauliSum) -> nx.Graph:
    
    """
    Creates a networkx graph corresponding to a specified problem Hamiltonian.

    Parameters
    ----------
    hamiltonian:
        The Hamiltonian of interest. Must be specified as a PauliSum object.

    Returns
    -------
    G:
        The corresponding networkx graph with the edge weights being the two-qubit coupling coefficients,
        and the node weights being the single-qubit bias terms.

    TODO

        Allow ndarrays to be input as hamiltonian too (?)

    """

    # Get hyperparameters from Hamiltonian
    hyperparams = {'nqubits': len(hamiltonian.get_qubits()), 'qubit_placeholders': [], 'singles': [], 'biases': [], 'pairs': [], 'couplings': []}
    
    for term in hamiltonian.terms:
        
        qubits_in_term = term.get_qubits()
        placeholders = [i for i in qubits_in_term if isinstance(i, QubitPlaceholder)]
        
        if len(qubits_in_term) == 1:
            
            if placeholders:
                qubits_in_term = [qubit_placeholder_id(*qubits_in_term)]
                
            hyperparams['singles'] += qubits_in_term                
            hyperparams['biases'] += [term.coefficient.real]
        
        elif len(qubits_in_term) == 2:
            
            for i in range(len(placeholders)):
                qubits_in_term[i] = qubit_placeholder_id(placeholders[i]) 
            
            hyperparams['pairs'] += [qubits_in_term]
            hyperparams['couplings'] += [term.coefficient.real]
            
        else:
            raise ValueError("Only single- and two-qubit terms supported in Hamiltonian currently")
        
    print(hyperparams)
        
    G = graph_from_hyperparams(*hyperparams.values())
    
    return G


def qubit_placeholder_id(qubit_placeholder):
    
    """
    Generate a simple string to identify a placeholder, intended for display purposes in Networkx graphs.
    
    Parameters
    ----------
    qubit_placeholder:
        A QubitPlaceholder object.
        
    Returns
    -------
    A string of the form "Holder ABC", where ABC are the last 3 digits of the QubitPlaceholder memory address.
    
    """
    
    if not isinstance(qubit_placeholder, QubitPlaceholder):
        raise TypeError("qubit_placeholder must be a QubitPlaceholder object")
        
    address_id = qubit_placeholder.__str__()[-4:-1]

    return "Holder " + str(address_id)

def hamiltonian_from_graph(G: nx.Graph) -> PauliSum:
    """
    Builds a cost Hamiltonian as a PauliSum from a specified networkx graph, extracting any node biases and edge weights.

    Parameters
    ----------
    G:
        The networkx graph of interest.

    Returns
    -------
    Hamiltonian
        The PauliSum representation of the networkx graph.

    """

    hamiltonian = []

    # Node bias terms
    bias_nodes = [*nx.get_node_attributes(G, 'weight')]
    biases = [*nx.get_node_attributes(G, 'weight').values()]
    for i in range(len(biases)):
        hamiltonian.append(PauliTerm("Z", bias_nodes[i], biases[i]))

    # Edge terms
    edges = list(G.edges)
    edge_weights = [*nx.get_edge_attributes(G, 'weight').values()]
    for i in range(len(edge_weights)):
        hamiltonian.append(
            PauliTerm("Z", edges[i][0], edge_weights[i]) * PauliTerm("Z", edges[i][1]))

    return PauliSum(hamiltonian)


def plot_graph(G, labels = {}):
    """
    Plots a networkx graph.

    Parameters
    ----------
    G:
        The networkx graph of interest.


    TODO:

        Allow the user to specify some desired plot properties?
    """

    #print(labels)
    #print(G.)

    weights = np.real([*nx.get_edge_attributes(G, 'weight').values()])
    pos = nx.shell_layout(G)

    nx.draw(G, pos, node_color='#A0CBE2', labels=labels, with_labels=True, edge_color=weights,
            width=4, edge_cmap=plt.cm.Blues)

    plt.show()


def graph_from_hyperparams(nqubits: int,
                           singles: List[int],
                           biases: List[float],
                           pairs: List[int],
                           couplings: List[float],
                           nplaceholders: int = None) -> nx.Graph:

    G = nx.Graph()

    # Add nodes with biases
    labels = {}
    for i in range(len(singles)):
        G.nodes[i]['weight'] = biases[i]
        G.nodes[i]['name'] = singles[i]
        labels[i] = singles[i]
        
    for i in range(len(pairs)):
        G.add_edge(str(pairs[i][0]), str(pairs[i][1]), weight=couplings[i])

    return G, labels

### HAMILTONIANS AND DATA ###

def hamiltonian_from_distance_matrix(dist, biases=None) -> PauliSum:
    """
    Generates a Hamiltonian from a distance matrix and a numpy array of single qubit bias terms where the i'th indexed value
    of in biases is applied to the i'th qubit. 

    Parameters
    ----------
    dist:      
        A 2-dimensional square matrix where entries in row i, column j represent the distance between node i and node j.
    biases:     
        A dictionary of floats, with keys indicating the qubits with bias terms, and corresponding values being the bias coefficients.

    Returns
    -------
    hamiltonian: 
        A PauliSum object modelling the Hamiltonian of the system  
    """
    
    pauli_list = list()
    m, n = dist.shape
    
    #allows tolerance for both matrices and dataframes
    if isinstance(dist,pd.DataFrame):
        dist = dist.values

    if biases:
        if not isinstance(biases, type(dict())):
            raise ValueError('biases must be of type dict()')
        for key in biases:
            term = PauliTerm('Z', key, biases[key])
            pauli_list.append(term)

        # pairwise interactions
    for i in range(m):
        for j in range(n):
            if i < j:
                term = PauliTerm('Z', i, dist[i][j]) * PauliTerm('Z', j)
                pauli_list.append(term)

    return PauliSum(pauli_list)


def distances_dataset(data, metric='euclidean'):
    """
    Computes the distance between data points in a specified dataset, according to the specified metric (default is Euclidean).

    Parameters
    ----------
    data:


    Returns
    -------


    TODO
        Decide what format the input and output should be.

    """

    if isinstance(data, dict):
        data = np.concatenate(list(data.values()))
    elif isinstance(data,pd.DataFrame):
        return pd.DataFrame(distance.cdist(data, data, metric),
                     index=data.index,columns=data.index)
    return distance.cdist(data, data, metric)


def gaussian_2Dclusters(n_clusters: int,
                        n_points: int,
                        means: List[float],
                        cov_matrices: List[float]):
    """
    Creates a set of clustered data points, where the distribution within each cluster is Gaussian.

    Parameters
    ----------
    n_clusters:
        The number of clusters
    n_points:
        A list of the number of points in each cluster
    means:
        A list of the means [x,y] coordinates of each cluster in the plane (i.e. their centre)
    cov_matrices:
        A list of the covariance matrices of the clusters

    Returns
    -------
    data
        A dict whose keys are the cluster labels, and values are a matrix of the with the x and y coordinates as its rows.

    TODO
        Decide on the format of the output here and redo code if needed, put -> in function header

    """
    args_in = [len(means), len(cov_matrices), len(n_points)]
    assert all(
        item == n_clusters for item in args_in), "Insufficient data provided for specified number of clusters"

    data = {}
    for i in range(n_clusters):

        cluster_mean = means[i]

        x, y = np.random.multivariate_normal(cluster_mean, cov_matrices[i], n_points[i]).T
        coords = np.array([x, y])
        tmp_dict = {str(i): coords.T}
        data.update(tmp_dict)

    return data


def plot_cluster_data(data):
    """
    Creates a scatterplot of the input data specified

    TODO
        Decide which format the input should be (ndarray, dataframe, etc)
    """

    data_matr = np.concatenate(list(data.values()))
    plt.scatter(data_matr[:, 0], data_matr[:, 1])
    plt.show()

### ANALYTIC FORMULAE ###


def ring_of_disagrees(n: int) -> PauliSum:
    """
    Builds the cost Hamiltonian for the "Ring of Disagrees" described in the original QAOA paper (https://arxiv.org/abs/1411.4028),
    for the specified number of vertices n.

    Parameters
    ----------
    n:
        Number of vertices in the ring

    Returns
    -------
    hamiltonian:
        The cost Hamiltonian representing the ring, as a PauliSum object.

    """

    hamiltonian = []
    for i in range(n - 1):
        hamiltonian.append(PauliTerm("Z", i, 0.5) * PauliTerm("Z", i + 1))
    hamiltonian.append(PauliTerm("Z", n - 1, 0.5) * PauliTerm("Z", 0))

    return PauliSum(hamiltonian)

### OTHER MISCELLANEOUS ###


def prepare_classical_state(reg, state: List) -> Program:
    """
    Prepare a custom classical state for all qubits in the specified register reg.

    Parameters
    ----------
    state :
       A list of 0s and 1s which represent the starting state of the register, bit-wise.

    Returns
    -------
    Program
       Quil Program with a circuit in an initial classical state.
    """

    if len(reg) != len(state):
        raise ValueError("qubit state must be the same length as reg")

    p = Program()
    for qubit, s in zip(reg, state):
        # if int(s) == 0 we don't need to add any gates, since the qubit is in state 0 by default
        if int(s) == 1:
            p.inst(X(qubit))
    return p


def return_lowest_state(probs):
    """
    Returns the lowest energy state of a QAOA run from the list of probabilities
    returned by pyQuil's Wavefunction.probabilities()method.

    Parameters
    ----------
    probs:
        A numpy array of length 2^n, returned by Wavefunction.probabilities()

    Returns
    -------
    lowest:
        A little endian list of binary integers indicating the lowest energy state of the wavefunction.
    """

    index_max = max(range(len(probs)), key=probs.__getitem__)
    string = '{0:0' + str(int(np.log2(len(probs)))) + 'b}'
    string = string.format(index_max)
    return [int(item) for item in string]


def evaluate_lowest_state(lowest, true):
    """
    Prints informative statements comparing QAOA's returned bit string to the true
    cluster values.

    Parameters
    ----------
    lowest:
        A little-endian list of binary integers representing the lowest energy state of the wavefunction
    true:
        A little-endian list of binary integers representing the true solution to the MAXCUT clustering problem.

    Returns
    -------
    Nothing
    """
    print('True Labels of samples:', true)
    print('Lowest QAOA State:', lowest)
    acc = accuracy_score(lowest, true)
    print('Accuracy of Original State:', acc * 100, '%')
    final_c = [0 if item == 1 else 1 for item in lowest]
    acc_c = accuracy_score(final_c, true)
    print('Accuracy of Complement State:', acc_c * 100, '%')


def plot_amplitudes(amplitudes, energies, ax=None):
    """
    Description
    -----------
    Makes a nice plot of the probabilities for each state and its energy

    Parameters
    ----------
    :param amplitudes: (array/list) the probabilites to find the state
    :param energies:   (array/list) The energy of that state
    :ax:               (matplotlib axes object) The canvas to draw on
    """
    if ax == None:
        fig, ax = plt.subplots()
    # normalizing energies
    energies = np.array(energies)
    energies /= max(abs(energies))

    format_strings = ('{0:00b}', '{0:01b}', '{0:02b}', '{0:03b}', '{0:04b}', '{0:05b}')
    nqubits = int(np.log2(len(energies)))

    # create labels
    labels = [r'$\left|' +
              format_strings[nqubits].format(i) + r'\right>$' for i in range(len(amplitudes))]
    y_pos = np.arange(len(amplitudes))
    width = 0.35
    ax.bar(y_pos, amplitudes**2, width, label=r'$|Amplitude|^2$')

    ax.bar(y_pos + width, -energies, width, label="-Energy")
    ax.set_xticks(y_pos + width / 2, minor=False)
    ax.set_xticklabels(labels, minor=False)
    #    plt.ylabel("Amplitude")
    ax.set_xlabel("State")
    ax.grid(linestyle='--')
    ax.legend()
    #    plt.show()

