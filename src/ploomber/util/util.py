from functools import wraps, reduce
import base64
from glob import glob
from pathlib import Path
from collections import defaultdict
import shutil
from pydoc import locate

import numpy as np

from ploomber.products import File


def requires(pkgs, name=None):
    """
    Check if packages were imported, raise ImportError with an appropriate
    message for missing ones
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            missing = [pkg for pkg in pkgs if locate(pkg) is None]

            if missing:
                msg = reduce(lambda x, y: x+' '+y, missing)
                fn_name = name or f.__name__

                raise ImportError('{} {} required to use {}. Install {} by '
                                  'running "pip install {}"'
                                  .format(msg,
                                          'is' if len(missing) == 1 else 'are',
                                          fn_name,
                                          'it' if len(
                                              missing) == 1 else 'them',
                                          msg))

            return f(*args, **kwargs)

        return wrapper

    return decorator


@requires(['matplotlib'])
def path2fig(path_to_image, dpi=50):
    # FIXME: having this import at the top causes trouble with the
    # multiprocessing library, moving it here solves the problem but we
    # have to find a better solution.
    # more info: https://stackoverflow.com/q/16254191/709975
    import matplotlib.pyplot as plt

    data = plt.imread(path_to_image)
    height, width, _ = np.shape(data)

    fig = plt.figure()
    fig.set_size_inches((width / dpi, height / dpi))
    ax = plt.Axes(fig, [0, 0, 1, 1])
    ax.set_axis_off()
    fig.add_axes(ax)
    ax.imshow(data)

    return fig


def safe_remove(path):
    if path.exists():
        if path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)


def image_bytes2html(data):
    fig_base64 = base64.encodebytes(data)
    img = fig_base64.decode("utf-8")
    html = '<img src="data:image/png;base64,' + img + '"></img>'
    return html


# TODO: finish or remove this
def clean_up_files(dag, interactive=True):
    """

    * Get all files generated by the dag
    * Find the set of parent directories
    * The parents should only have the files that are generated by tge DAG

    """
    # WIP
    # get products that generate Files
    paths = [Path(str(t.product)) for t in dag.values()
             if isinstance(t.product, File)]
    # each file generates a .source file, also add it
    paths = [(p, Path(str(p) + '.source')) for p in paths]
    # flatten list
    paths = [p for tup in paths for p in tup]

    # get parents
    parents = set([p.parent for p in paths])

    # map parents to its files
    parents_map = defaultdict(lambda: [])

    for p in paths:
        parents_map[str(p.parent)].append(str(p))

    extra_all = []

    # for every parent, find the extra files
    for p in parents:
        existing = glob(str(p) + '/*')
        products = parents_map[str(p)]

        extra = set(existing) - set(products)
        extra_all.extend(list(extra))

    for p in extra_all:
        if interactive:
            answer = input('Delete {} ? (y/n)'.format(p))

            if answer == 'y':
                safe_remove(p)
                print('Deleted {}'.format(p))


def isiterable(obj):
    try:
        iter(obj)
    except TypeError:
        return False
    else:
        return True
