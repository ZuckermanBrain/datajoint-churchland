
"""Data visualization.

Todo:
    * overlay multiple attributes
    * apply functions to attributes
    * colormaps
"""

import datajoint as dj
import inspect, re, math
import numpy as np
import matplotlib.pyplot as plt, matplotlib.colors as mplcol
import colorcet as cc
from typing import NewType, Tuple, List, Any

import timeit

DataJointTable = dj.user_tables.OrderedClass

# -------
# GLOBALS
# -------

# default figure settings
DEFAULT = dict(
    layout = dict(
        figsize=(12,8),
        n_rows=None,
        n_columns=None,
        grid_attr=(),
        orientation=None,
        limit_figures=10,
        limit_subplots=25,
        limit_layers=500,
        limit_rows=50,
        limit_columns=10,
    ),
    style = dict(
        kind='line',
        marker_size=3,
        color=None,
        color_map=cc.blues,
        reverse_color_map=False,
        remove_spines=('top', 'right'),
        show_x_ticks=True,
        show_y_ticks=True,
    ),
    axes = dict(
        sharex=False,
        sharey=False,
        x_lim=(None, None),
        y_lim=(None, None),
        y_tick_step=None,
        show_legend=False,
        sparse_legend=False,
    )
)


# ----------
# PLOT TABLE
# ----------

def plot_table(
    table: DataJointTable, 
    y: str,
    x: str=None,
    group_by: Tuple[str]=(),
    stack_by: Tuple[str]=(),
    ignore: Tuple[str]=(),
    track: Tuple[str]=(),
    map_fcn: Any=None,
    map_args: Any=None,
    layout: dict=None,
    style: dict=None,
    axes: dict=None,
    labels: dict=None,
    ) -> None:
    """Plot DataJoint table.

    Flexible function for plotting any attribute from a DataJoint table.
    Generates one or more figures composed of one or more subplots.
    Use optional group_by parameter to specify which attributes to aggregate within a figure.
    Use optional stack_by parameter to specify which attributes to stack within a subplot.
    Add layout, style, axes dictionarys to overwrite default parameters.
    Add labels dict to convert attribute names to axes labels/figure titles.

    Args:
        table (DataJointTable): table (base or derived)
        y (str): attribute name to plot on y-axis
        x (str, optional): attribute name to plot y-data against. Defaults to None.
        group_by (List[str], optional): attributes to group plotted data within a figure. Defaults to None.
        stack_by (List[str], optional): attributes to stack plotted data within a subplot. Defaults to None.
        layout (dict, optional): layout parameters. Defaults to None.
        style (dict, optional): plot style parameters. Defaults to None.
        axes (dict, optional): axes parameters. Defaults to None.
        labels (dict, optional): attribute name to figure text mapping. Defaults to None.
    """

    # update defaults with inputs
    if layout:
        layout = dict(DEFAULT['layout'], **layout)
    else:
        layout = DEFAULT['layout'].copy()

    if style:
        style = dict(DEFAULT['style'], **style)
    else:
        style = DEFAULT['style'].copy()
    
    if axes:
        axes = dict(DEFAULT['axes'], **axes)
    else:
        axes = DEFAULT['axes'].copy()

    # setup pages
    layout_keys = make_figure_layout(table, group_by, stack_by, ignore, track, layout)

    # initialize key and data attributes
    key_attributes = list(filter(None, track))
    data_attributes = list(filter(None, [x] + [y]))

    # fetch data
    data_set = table.proj(*(key_attributes + data_attributes)).fetch(as_dict=True)

    # append table primary keys to set of key attributes
    key_attributes = set(key_attributes + table.primary_key) - set(list(filter(None, ignore)))

    # split key and data attributes
    data_keys = [{k: v for k, v in d.items() if k in key_attributes} for d in data_set]
    data_set = [{k: v for k, v in d.items() if k in data_attributes} for d in data_set]

    # plot data
    for layout_key in layout_keys:

        n_rows, n_columns = layout_key['subplot'].shape

        fig, axs = plt.subplots(n_rows, n_columns, figsize=layout['figsize'], sharex=axes['sharex'], sharey=axes['sharey'])

        axs = np.array(axs).reshape((n_rows, n_columns))

        figure_key = layout_key['figure']
        subplot_keys = layout_key['subplot'].flatten()

        for nd_idx, plot_key, layer_keys \
            in zip(np.ndindex((n_rows, n_columns)), subplot_keys, layout_key['layer']):

            if plot_key is None:
                axs[nd_idx].axis('off')
                continue

            # aggregate keys
            if np.any(layer_keys):
                axs_keys = [dict(figure_key, **plot_key, **layer_key) for layer_key in layer_keys]
            else:
                axs_keys = [dict(figure_key, **plot_key)]                

            # extract x and y data from datasets
            data = [d for d, k in zip(data_set, data_keys) if k in axs_keys]

            y_data = np.array([d[y] for d in data])

            if map_fcn:
                y_data = np.array([map_fcn(y, *list(filter(None, map_args))) for y in y_data])

            n_trials, n_samples = y_data.shape

            if x:
                x_data = np.array([d[x] for d in data])
            else:
                x_data = np.repeat(np.arange(n_samples)[np.newaxis,:], n_trials, axis=0)

            # ensure matched x-y data lengths
            if x_data.shape[1] != n_samples:
                x_data = np.repeat(np.linspace(x_data.min(), x_data.max(), n_samples)[np.newaxis,:], n_trials, axis=0)

            # set color map
            if style['color'] is not None:
                cmap = np.repeat(style['color'], n_trials)
            else:
                cmap = mplcol.LinearSegmentedColormap.from_list('cmap', style['color_map'])
                cmap = cmap(np.linspace(0, 1, n_trials))

            if style['reverse_color_map']:
                cmap = np.flipud(cmap)

            # plot data
            if style['kind'] == 'line':
                for trial, (kk, xx, yy, cc) in enumerate(zip(axs_keys, x_data, y_data, cmap)):

                    if (labels is not None and stack_by) \
                        and (stack_by[0] in labels.keys()) \
                        and axes['show_legend']:

                        line_label = labels[stack_by[0]].format(kk[stack_by[0]])
                    else:
                        line_label = ''

                    if axes['sparse_legend'] and trial in range(1, len(axs_keys)-1):
                        line_label = ''

                    axs[nd_idx].plot(xx, yy, color=cc, label=line_label);

            elif style['kind'] == 'raster':
                for trial, (xx, yy, cc) in enumerate(zip(x_data, y_data, cmap)):
                    spk_idx = np.flatnonzero(yy)
                    if np.any(spk_idx):
                        axs[nd_idx].scatter(
                            xx[spk_idx], np.repeat(trial, len(spk_idx)), c=cc, s=style['marker_size']
                        )

            # format x-axis
            axs[nd_idx].set_xlim([x_data.min(), x_data.max()])               

            if any(map(lambda x: x is not None, axes['x_lim'])):
                axs[nd_idx].set_xlim([
                    (axes['x_lim'][0] if axes['x_lim'][0] is not None else axs[nd_idx].get_xlim()[0]),
                    (axes['x_lim'][1] if axes['x_lim'][1] is not None else axs[nd_idx].get_xlim()[1])
                ])

            # format y-axis
            if any(map(lambda x: x is not None, axes['y_lim'])):
                axs[nd_idx].set_ylim([
                    (axes['y_lim'][0] if axes['y_lim'][0] is not None else np.floor(y_data.min())),
                    (axes['y_lim'][1] if axes['y_lim'][1] is not None else np.ceil(y_data.max()))
                ])

            y_lim = axs[nd_idx].get_ylim()

            if axes['y_tick_step']:
                axs[nd_idx].set_ylim([
                    min(0, min(y_lim[0], np.floor(y_data.min() / axes['y_tick_step']) * axes['y_tick_step'])), 
                    max(y_lim[1], np.ceil(y_data.max() / axes['y_tick_step']) * axes['y_tick_step'])
                ])
                y_lim = axs[nd_idx].get_ylim()
                axs[nd_idx].set_yticks(np.arange(y_lim[0], y_lim[1]+axes['y_tick_step'], axes['y_tick_step']))

            # format spines
            if any(style['remove_spines']):
                [axs[nd_idx].spines[edge].set_visible(False) for edge in style['remove_spines']];

            # format ticks
            if not style['show_x_ticks']:
                axs[nd_idx].set_xticks([])

            if not style['show_y_ticks']:
                axs[nd_idx].set_yticks([])

            # legend
            if axes['show_legend']:
                axs[nd_idx].legend()

            # label axes
            if labels is not None:

                # x-axis
                if x in labels.keys():
                    axs[nd_idx].set_xlabel(labels[x])

                if layout['grid_attr']:

                    row_attr, col_attr = layout['grid_attr']

                    # y-axis
                    if row_attr in labels.keys() and nd_idx[1] == 0:
                        axs[nd_idx].set_ylabel(labels[row_attr].format(plot_key[row_attr]))

                    # title
                    if col_attr in labels.keys() and nd_idx[0] == 0:
                        axs[nd_idx].set_title(labels[col_attr].format(plot_key[col_attr]))

                else:
                    # y-axis
                    if y in labels.keys():
                        axs[nd_idx].set_ylabel(labels[y])

                    # subplot
                    if labels:
                        subplot_title = [labels[key].format(plot_key[key]) for key in plot_key.keys() if key in labels.keys()]
                        axs[nd_idx].set_title('. '.join(subplot_title))

        # adjust subplot layout
        fig.tight_layout(rect=[0, 0.03, 1, 0.95])

        # figure title
        if labels:
            figure_title = [labels[key].format(figure_key[key]) for key in figure_key.keys() if key in labels.keys()]
            fig.suptitle('. '.join(figure_title))


# ------------------
# MAKE FIGURE LAYOUT
# ------------------

def make_figure_layout(
    table: DataJointTable,
    group_by: Tuple[str]=(),
    stack_by: Tuple[str]=(),
    ignore: Tuple[str]=(),
    track: Tuple[str]=(),
    layout: dict=None,
    ):
    """Make figure layout."""

    # update default layout with input
    if layout:
        layout = dict(DEFAULT['layout'], **layout)
    else:
        layout = DEFAULT['layout'].copy()

    # tracked attributes
    tracked_attributes = set(tuple(table.primary_key) + track) - set(ignore)

    # merge grid attr with group attributes
    if layout['grid_attr']:
        group_by = layout['grid_attr']

    # check group/stack attributes
    assert set(group_by) <= tracked_attributes, 'Group {} not in primary keys'.format(group_by)
    assert set(stack_by) <= tracked_attributes, 'Stack {} not in primary keys'.format(stack_by)

    # get figure keys from attributes not in group or stack
    separate_by = [attr for attr in tracked_attributes if attr not in group_by + stack_by]
    figure_keys = (dj.U(*separate_by) & table).fetch('KEY')
    n_figures = len(figure_keys)

    # limit figure keys
    max_figures = layout['limit_figures']
    if max_figures and n_figures > max_figures:

        print('Limiting {} figures to {}. Set layout[\'limit_figures\']=None to display all figures'\
            .format(n_figures, max_figures))
        figure_keys = figure_keys[:max_figures]

    # make layout key set
    layout_keys = [{'figure': fig_key, 'subplot': None, 'layer': None} for fig_key in figure_keys]

    # add subplot and layer keys to set
    for layout_key in layout_keys:

        def limit_subplots(keys):

            max_subplots = layout['limit_subplots']
            if max_subplots and len(keys) > max_subplots:

                print('Limiting {} subplots to {}. Set layout[\'limit_subplots\']=None to display all subplots'\
                    .format(len(keys), max_subplots))
                keys = keys[:max_subplots]

            return keys

        # set subplot keys
        if layout['grid_attr']: # infer from grid attributes

            # fetch column keys
            column_keys = np.array((dj.U(layout['grid_attr'][1]) & table).fetch('KEY', order_by=layout['grid_attr'][1]))

            # limit columns
            n_columns = len(column_keys)
            max_columns = layout['limit_columns']
            if max_columns and n_columns > max_columns:

                print('Limiting {} columns to {}. Set layout[\'limit_columns\']=None to display all columns'\
                    .format(n_columns, max_columns))
                column_keys = column_keys[:max_columns]

            # update column count
            layout.update(n_columns=len(column_keys))

            # fetch row keys (fetching dj.U keys is much faster than fetching the attribute directly)
            row_keys = np.array([(dj.U(layout['grid_attr'][0]) & (table & column_key)).fetch('KEY', order_by=layout['grid_attr'][0]) for column_key in column_keys])

            # limit rows
            max_rows = layout['limit_rows']
            for column_idx, row_key_set in enumerate(row_keys):
                n_rows = len(row_key_set)
                if max_rows and n_rows > max_rows:

                    print('Limiting column {} with {} rows to {}. Set layout[\'limit_rows\']=None to display all rows'\
                        .format(column_idx, n_rows, max_rows))
                    row_keys[column_idx] = row_key_set[:max_rows]
            
            # update row count
            layout.update(n_rows=max(map(len, row_keys)))

            # assign row/column keys to subplot keys
            subplot_keys = np.tile(dict(), (layout['n_rows'], layout['n_columns']))
            for row_idx, column_idx in np.ndindex(subplot_keys.shape):
                if row_idx < len(row_keys[column_idx]):
                    subplot_keys[row_idx, column_idx] = dict(row_keys[column_idx][row_idx], **column_keys[column_idx]) 
                else:
                    subplot_keys[row_idx, column_idx] = None

        else: # infer from group attributes

            if group_by:
                subplot_keys = (dj.U(*group_by) & (table & layout_key['figure'])).fetch('KEY')
            else:
                subplot_keys = [{}]

            subplot_keys = limit_subplots(subplot_keys)
            n_subplots = len(subplot_keys)

            if not layout['n_rows'] or layout['n_columns']:

                layout.update(n_columns=np.ceil(np.sqrt(n_subplots)).astype(int))
                layout.update(n_rows=np.ceil(n_subplots/layout['n_columns']).astype(int))

            elif layout['n_rows'] and not layout['n_columns']:

                layout.update(n_columns=np.ceil(n_subplots/layout['n_rows']).astype(int))

            elif layout['n_columns'] and not layout['n_rows']:

                layout.update(n_rows=np.ceil(n_subplots/layout['n_columns']).astype(int))

            # extend subplot keys to grid size
            subplot_keys.extend([None] * ((layout['n_rows'] * layout['n_columns']) - len(subplot_keys)))

            # reshape subplot keys as array
            subplot_keys = np.array(subplot_keys).reshape((layout['n_rows'], layout['n_columns']))

        # add subplot keys to layout key set
        layout_key['subplot'] = subplot_keys

        # get layer keys
        if stack_by:

            layer_keys = np.array([np.array((dj.U(*stack_by) & (table & layout_key['figure'] & subplot_key)).fetch('KEY')) \
                if subplot_key is not None else None for subplot_key in layout_key['subplot'].ravel()])
        else:
            layer_keys = np.repeat(dict(), len(layout_key['subplot'].ravel()))

        # limit non-empty layer keys
        max_layers = layout['limit_layers']
        for idx, layer_key_set in enumerate(layer_keys):
            if np.any(layer_key_set):
                n_layers = len(layer_key_set)
                if max_layers and n_layers > max_layers:

                    print('Limiting plot {} with {} layers to {}. Set layout[\'limit_layers\']=None to display all layers'\
                        .format(idx, n_layers, max_layers))
                    layer_key_set = layer_key_set[:max_layers]

        layout_key['layer'] = layer_keys

    return layout_keys
