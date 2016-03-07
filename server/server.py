#!/usr/bin/env python3

"""Runs a user interface for the interactive anchor words algorithm"""

import json
import os
import random

import flask

import ankura
from ankura import label

app = flask.Flask(__name__, static_url_path='')


@ankura.util.memoize
@ankura.util.pickle_cache('fcc.pickle')
def get_newsgroups():
    """Retrieves the 20 newsgroups dataset"""
    filenames = '/local/cojoco/git/fcc/documents/*.txt'
#    news_glob = '/local/cojoco/git/jeffData/newsgroups/*/*'
    engl_stop = '/local/cojoco/git/jeffData/stopwords/english.txt'
    news_stop = '/local/cojoco/git/jeffData/stopwords/newsgroups.txt'
    name_stop = '/local/cojoco/git/fcc/stopwords/names.txt'
    curse_stop = '/local/cojoco/git/jeffData/stopwords/profanity.txt'
    pipeline = [(ankura.read_glob, filenames, ankura.tokenize.news),
                (ankura.filter_stopwords, engl_stop),
                (ankura.filter_stopwords, news_stop),
                (ankura.combine_words, name_stop, '<name>', ankura.tokenize.simple),
                (ankura.combine_words, curse_stop, '<profanity>', ankura.tokenize.simple),
                (ankura.filter_rarewords, 200),
                (ankura.filter_commonwords, 150000)]
    dataset = ankura.run_pipeline(pipeline)
    return dataset


@ankura.util.memoize
@ankura.util.pickle_cache('fcc-anchors-default.pickle')
def default_anchors():
    """Retrieves default anchors for newsgroups using Gram-Schmidt"""
    dataset = get_newsgroups()
    anchors, indices = ankura.gramschmidt_anchors(dataset, 20, 500,
                                                  return_indices=True)
    anchor_tokens = [[dataset.vocab[index]] for index in indices]
    return anchor_tokens, anchors


@ankura.util.memoize
def user_anchors(anchor_tokens):
    """Computes multiword anchors from user specified anchor tokens"""
    return ankura.multiword_anchors(get_newsgroups(), anchor_tokens)


@app.route('/')
def serve_itm():
    """Serves the Interactive Topic Modeling UI"""
    return app.send_static_file('index.html')


@app.route('/finished', methods=['GET', 'POST'])
def save_user_data():
    """Receives and saves user data when done button is clicked in the ITM UI"""
    flask.request.get_data()
    input_json = flask.request.get_json(force=True)
    with ankura.util.open_unique(dirname='user_data') as data_file:
        json.dump(input_json, data_file)
    return 'OK'


@app.route('/vocab')
def get_vocab():
    """Returns all valid vocabulary words in the dataset"""
    return flask.jsonify(vocab=get_newsgroups().vocab)


@app.route('/topics')
def topic_request():
    """Performs a topic request using anchors from the query string"""
    dataset = get_newsgroups()

    # get the anchors (both tokens and vector) from the request
    raw_anchors = flask.request.args.get('anchors')
    if raw_anchors is None:
        anchor_tokens, anchors = default_anchors()
    else:
        anchor_tokens = ankura.util.tuplize(json.loads(raw_anchors))
        anchors = user_anchors(anchor_tokens)

    # infer the topics from the anchors
    topics = ankura.recover_topics(dataset, anchors)
    topic_summary = ankura.topic.topic_summary(topics, dataset, n=15)

    # optionally produce an example of the resulting topics
    example = flask.request.args.get('example')
    if example is None:
        # no examples were request
        docdata = None
    else:
        if not example:
            # an example was requested, by no dirname given - pick one
            sample_doc = random.randrange(dataset.num_docs)
            example = dataset.doc_metadata(sample_doc, 'dirname')

        # perform topic inference on each of the requested documents
        docdata = []
        for doc in dataset.metadata_query('dirname', example):
            doc_tokens = dataset.doc_tokens(doc)
            _, doc_topics = ankura.topic.predict_topics(topics, doc_tokens)
            docdata.append({'text': dataset.doc_metadata(doc, 'text'),
                            'topics': sorted({int(x) for x in doc_topics})})

    return flask.jsonify(anchors=anchor_tokens,
                         topics=topic_summary,
                         example=docdata)


if __name__ == '__main__':
    # call these to trigger pickle_cache
    get_newsgroups()
    default_anchors()

    # start the server, with the data already cached
    app.run(debug=True, host='0.0.0.0')
