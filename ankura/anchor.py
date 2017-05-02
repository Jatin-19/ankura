"""Functions for anchor selection"""

import collections
import numpy


def random_projection(A, k):
    """Randomly reduces the dimensionality of a n x d matrix A to k x d

    Follows the method given by Achlioptas 2001 which yeilds a projection which
    preserves pairwise distances within some small factor.
    """
    R = numpy.random.choice([-1, 0, 0, 0, 0, 1], (A.shape[1], k))
    return numpy.dot(A, R * numpy.sqrt(3))


def gram_schmidt(corpus, Q, k, doc_threshold=500, project_dim=1000):
    """Uses stabalized Gram-Schmidt decomposition to find k anchors.
    """
    # Find candidate anchors
    counts = collections.Counter()
    for doc in corpus.documents:
        counts.update(set(t.type for t in doc.types))
    candidates = [tid for tid, count in counts.items() if count > doc_threshold]

    # Row-normalize and project Q, preserving the original Q
    Q_orig = Q
    Q = Q / Q.sum(axis=1, keepdims=True)
    if project_dim:
        Q = random_projection(Q, project_dim)

    # Setup book keeping
    indices = numpy.zeros(k, dtype=numpy.int)
    basis = numpy.zeros((k-1, Q.shape[1]))

    # Find the farthest point from the origin
    max_dist = 0
    for i in candidates:
        dist = numpy.linalg.norm(Q[i])
        if dist > max_dist:
            max_dist = dist
            indices[0] = i

    # Translate all points to the new origin
    for i in candidates:
        Q[i] = Q[i] - Q[indices[0]]

    # Find the farthest point from origin
    max_dist = 0
    for i in candidates:
        dist = numpy.linalg.norm(Q[i])
        if dist > max_dist:
            max_dist = dist
            indices[1] = i
    basis[0] = Q[indices[1]] / max_dist

    # Stabilized gram-schmidt to finds new anchor words to expand the subspace
    for j in range(1, k - 1):
        # Project all the points onto the basis and find the farthest point
        max_dist = 0
        for i in candidates:
            Q[i] = Q[i] - numpy.dot(Q[i], basis[j-1]) * basis[j - 1]
            dist = numpy.dot(Q[i], Q[i])
            if dist > max_dist:
                max_dist = dist
                indices[j + 1] = i
                basis[j] = Q[i] / numpy.sqrt(numpy.dot(Q[i], Q[i]))

    # Use the original Q to extract anchor vectors using the anchor indices
    return Q_orig[indices, :]
