
"""Data visualization.

Todo:
    * populatedependents
"""

import datajoint as dj
import inspect, re, math
import numpy as np
import matplotlib.pyplot as plt
from typing import NewType, Tuple, List

DataJointTable = dj.user_tables.OrderedClass

def plot_table(
        table: DataJointTable, 
        y_attribute: str,
        x_attribute: str=None,
        group_by: List[str]=None,
        stack_by: List[str]=None,
        plot_style: str='lines',
        marker_size: int=3,
        plot_mean: bool=False,
        plot_ste: bool=False,
        trial_type: Tuple[str]='good',
        figsize: Tuple[int,int]=(12,8),
        n_rows: int=None,
        n_columns: int=None,
        y_tick_step: int=None,
        limit_figures: int=None,
        limit_subplots: int=None,
        limit_lines: int=None,
        attribute_label: dict={}
    ) -> None:
        """Plot DataJoint table."""

        # standardize input format
        if not group_by:
            group_by = []

        if not stack_by:
            stack_by = []

        if isinstance(trial_type, str):
            trial_type = (trial_type,)

        # check inputs
        assert set(group_by) <= set(table.primary_key), 'Group attribute {} not in primary key'.format(group_by)
        assert set(stack_by) <= set(table.primary_key), 'Stack attribute {} not in primary key'.format(group_by)
        assert set(trial_type) <= {'good','bad'},      'Unrecognized trial type {}'.format(trial_type)

        # filter by trial type
        if 'good' in trial_type and not 'bad' in trial_type:
            table = table & {'good_trial': 1}
        
        elif 'bad' in trial_type and not 'good' in trial_type:
            table = table & {'good_trial': 0}

        # get figure keys by non-grouping or stacking attributes
        separate_by = [attr for attr in table.primary_key if attr not in group_by + stack_by]
        figure_keys = (dj.U(*separate_by) & table).fetch('KEY')

        # downsample figure keys
        if limit_figures:
            figure_keys = figure_keys[:min(len(figure_keys),limit_figures)]

        #== LOOP FIGURES ==
        for fig_key in figure_keys:
            
            # get subplot keys as unique grouping attributes 
            if group_by:
                subplot_keys = (dj.U(*group_by) & (table & fig_key)).fetch('KEY')
            else:
                subplot_keys = [fig_key]

            # downsample subplot keys
            if limit_subplots:
                subplot_keys = subplot_keys[:min(len(subplot_keys),limit_subplots)]

            n_subplots = len(subplot_keys)

            # setup page
            if not (n_columns or n_rows):
                n_columns = np.ceil(np.sqrt(n_subplots)).astype(int)
                n_rows = np.ceil(n_subplots/n_columns).astype(int)

            elif n_columns and not n_rows:
                n_rows = np.ceil(n_subplots/n_columns).astype(int)

            elif n_rows and not n_columns:
                n_columns = np.ceil(n_subplots/n_rows).astype(int)

            else:
                subplot_keys = subplot_keys[:min(len(subplot_keys), n_rows*n_columns)]

            # create axes handles and ensure indexable
            fig, axs = plt.subplots(n_rows, n_columns, figsize=figsize, sharey=True)

            if n_rows == 1 and n_columns == 1:
                axs = np.array(axs)
            
            axs = axs.reshape((n_rows, n_columns))

            #== LOOP SUBPLOTS ==
            for idx, plot_key in zip(np.ndindex((n_rows, n_columns)), subplot_keys):

                # get line keys as unique stacking attributes
                if stack_by:
                    line_keys = (dj.U(*stack_by) & (table & fig_key & plot_key)).fetch('KEY')
                else:
                    line_keys = {}

                # get plot attribute
                y = np.stack((table & fig_key & plot_key & line_keys).fetch(y_attribute))

                # x value
                if x_attribute:
                    x = (table & fig_key & plot_key & line_keys).fetch(x_attribute, limit=1)[0]

                else:
                    x = np.arange(y.shape[1])

                # plot x-y values
                if plot_style == 'lines':

                    axs[idx].plot(x, y.T, 'k');

                elif plot_style == 'raster':

                    for yi, yy in enumerate(y):
                        axs[idx].scatter(x[np.flatnonzero(yy)], yi + yy[np.flatnonzero(yy)], c='k', s=marker_size)

                # plot mean
                if plot_mean:
                    axs[idx].plot(x, y.mean(axis=0), 'b');

                # plot standard error
                if plot_ste and len(line_keys) > 1:
                    mu = y.mean(axis=0)
                    std = y.std(axis=0, ddof=1)
                    ste = std / y.shape[0]
                    axs[idx].plot(x, mu + ste, 'b--');
                    axs[idx].plot(x, mu - ste, 'b--');

                # format axes
                axs[idx].set_xlim(x[[0,-1]])
                y_lim = axs[idx].get_ylim()

                if y_tick_step:
                    axs[idx].set_ylim([
                        min(0, min(y_lim[0], np.floor(y.min() / y_tick_step) * y_tick_step)), 
                        max(y_lim[1], np.ceil(y.max() / y_tick_step) * y_tick_step)
                    ])
                    y_lim = axs[idx].get_ylim()
                    axs[idx].set_yticks(np.arange(y_lim[0], y_lim[1]+y_tick_step, y_tick_step))

                # set x-axis label
                if x_attribute in attribute_label.keys():
                    axs[idx].set_xlabel(attribute_label[x_attribute])

                # set y-axis label
                if y_attribute in attribute_label.keys():
                    axs[idx].set_ylabel(attribute_label[y_attribute])

                # format figure
                [axs[idx].spines[edge].set_visible(False) for edge in ['top','right']];

                # add subplot title
                axs[idx].set_title(
                    '. '.join([attribute_label[key].format(plot_key[key]) for key in plot_key.keys() if key in attribute_label.keys()])
                )

            # adjust subplot layout
            fig.tight_layout(rect=[0, 0.03, 1, 0.95])

            # add figure title
            if n_subplots > 1:
                fig.suptitle(
                    '. '.join([attribute_label[key].format(fig_key[key]) for key in fig_key.keys() if key in attribute_label.keys()])
                )