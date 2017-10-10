#!/usr/bin/python
# -*-coding: utf-8 -*-
# Author: Joses Ho
# Email : joseshowh@gmail.com

"""
Plot functions for espresso objects.
"""

#      # #####  #####    ##   #####  #   #    # #    # #####   ####  #####  #####
#      # #    # #    #  #  #  #    #  # #     # ##  ## #    # #    # #    #   #
#      # #####  #    # #    # #    #   #      # # ## # #    # #    # #    #   #
#      # #    # #####  ###### #####    #      # #    # #####  #    # #####    #
#      # #    # #   #  #    # #   #    #      # #    # #      #    # #   #    #
###### # #####  #    # #    # #    #   #      # #    # #       ####  #    #   #

import sys as _sys
_sys.path.append("..") # so we can import munger from the directory above.

import numpy as _np
import pandas as _pd

import matplotlib.pyplot as _plt
import matplotlib.patches as _mpatches # for custom legends.

import seaborn as _sns
import bootstrap_contrast as _bsc

from . import plot_helpers as _plot_helpers
from .._munger import munger as _munger

# Add submodules below. The respective .py scripts
# should be in the same folder as espresso_plotter.py.
from . import contrast as _contrast
from . import cumulative as _cumulative
from . import timecourse as _timecourse


class espresso_plotter():
    """
    Plotting class for espresso object.

    Plots available:
        rasters
        percent_feeding

    To produce contrast plots, use the `contrast` method.
    e.g `my_espresso_experiment.plot.contrast`

        Plots available:
            feed_count_per_fly

    To produce timecourse plots, use the `timecourse` method.
    e.g `my_espresso_experiment.plot.timecourse`

        Plots available:
            TBA
    """

    #    #    #    #    #####
    #    ##   #    #      #
    #    # #  #    #      #
    #    #  # #    #      #
    #    #   ##    #      #
    #    #    #    #      #

    def __init__(self,espresso): # pass along an espresso instance.

        # Create attribute so the other methods below can access the espresso object.
        self._experiment=espresso
        # call obj.plot.xxx to access these methods.
        self.contrast=_contrast.contrast_plotter(self)
        self.timecourse=_timecourse.timecourse_plotter(self)
        self.cumulative=_cumulative.cumulative_plotter(self)


    #####    ##    ####  ##### ###### #####     #####  #       ####  #####  ####
    #    #  #  #  #        #   #      #    #    #    # #      #    #   #   #
    #    # #    #  ####    #   #####  #    #    #    # #      #    #   #    ####
    #####  ######      #   #   #      #####     #####  #      #    #   #        #
    #   #  #    # #    #   #   #      #   #     #      #      #    #   #   #    #
    #    # #    #  ####    #   ###### #    #    #      ######  ####    #    ####


    def rasters(self,
                group_by=None,
                color_by=None,
                add_flyid_labels=False,
                fig_size=None,
                ax=None,
                gridlines_major=True,
                gridlines_minor=True):
        """
        Produces a raster plot of feed events.

        Keywords
        --------

        group_by: string, default None
            The categorical column in the espresso object used to group the raster plots.
            Categories in the column will be tiled horizontally as panels.

        color_by: string, default None
            The categorical column in the espresso object used to color individual feeds.

        add_flyid_labels: boolean, default True
            If True, the FlyIDs for each fly will be displayed on the left of each raster row.

        fig_size: tuple (width, height), default None
            The size of the final figure, in inches.

        ax: matplotlib Axes, default None
            Plot on specified matplotlib Axes.

        gridlines_major, gridlines_minor: boolean, default True
            Whether or not major and minor vertical gridlines are displayed.

        Returns
        -------
        matplotlib AxesSubplot(s)
        """
        # make a copy of the metadata and the feedlog.
        allfeeds=self._experiment.feeds.copy()
        allflies=self._experiment.flies.copy()

        # Handle the group_by and color_by keywords.
        group_by, color_by = _munger.check_group_by_color_by(group_by, color_by, allfeeds)

        print( "Coloring rasters by {0}".format(color_by) )
        print( "Grouping rasters by {0}".format(group_by) )

        if color_by==group_by: # catch as exception:
            raise ValueError('color_by and group_by both have the same value. They should be 2 different column names in the feedlog.')

        # Get the total flycount.
        try:
            check_grpby_col=allflies.groupby(group_by)
            maxflycount=check_grpby_col.count().FlyID.max()
        except KeyError:
            # group_by is not a column in the metadata,
            # so we assume that the number of flies in the raster plot
            # is simply the total number of flies.
            maxflycount=len(allflies)

        # Get the groups we will be grouping on, and coloring on.
        groupby_grps=_np.sort(allfeeds[group_by].unique())
        color_grps=_np.sort(allfeeds[color_by].unique())
        num_plots=int( len(groupby_grps) )

        # Create the palette.
        colors=_plot_helpers._make_categorial_palette(allfeeds,color_by)
        palette=dict( zip(color_grps, colors) )

        # Create custom handles for the foodchoice.
        # See http://matplotlib.org/users/legend_guide.html#using-proxy-artist
        raster_legend_handles=[]
        for key in palette.keys():
            patch=_mpatches.Patch(color=palette[key], label=key)
            raster_legend_handles.append(patch)

        # Initialise the figure.
        _sns.set(style='ticks',context='poster')
        if add_flyid_labels:
            ws=0.4
        else:
            ws=0.2
        if fig_size is None:
            x_inches=10*num_plots
            y_inches=7
        else:
            if isinstance(fig_size, tuple) or isinstance(fig_size, list):
                x_inches=fig_size[0]
                y_inches=fig_size[1]
            else:
                raise ValueError('Please make sure fig_size is a tuple of the form (w,h) in inches.')

        if ax is None:
            fig,axx=_plt.subplots(nrows=1,
                                  ncols=num_plots,
                                  figsize=(x_inches,y_inches),
                                  gridspec_kw={'wspace':ws} )
        else:
            axx=ax
            if len(axx)!=num_plots:
                raise ValueError('The length of the supplied array of Axes objects does not match the number of groups in {0}.'.format(group_by))

        # Loop through each panel.
        for c, grp in enumerate( groupby_grps ):
            if len(groupby_grps)>1:
                rasterax=axx[c]
            else:
                rasterax=axx
            print('plotting {0} {1}'.format(grp,'rasters'))
            print('Be patient, this can a while!')

            # Plot the raster plots.
            ## Plot vertical grid lines if desired.
            grid_kwargs=dict(linestyle=':', alpha=0.5)
            if gridlines_major:
                rasterax.xaxis.grid(which='major',linewidth=0.25,**grid_kwargs)
            if gridlines_minor:
                rasterax.xaxis.grid(which='minor',linewidth=0.15,**grid_kwargs)

            ## Grab only the flies we need.
            tempfeeds=allfeeds[allfeeds[group_by]==grp].copy()
            temp_allflies=tempfeeds.FlyID.unique().tolist()

            ## Order the flies properly.
            ### First, drop non-valid feeds, then sort by feed time and feed duration,
            ### then pull out FlyIDs in that order.
            temp_feeding_flies=tempfeeds[~_np.isnan(tempfeeds['FeedDuration_s'])].\
                                    sort_values(['RelativeTime_s','FeedDuration_s']).FlyID.\
                                    drop_duplicates().tolist()
            ### Next, identify which flies did not feed (aka not in list above.)
            temp_non_feeding_flies=[fly for fly in temp_allflies if fly not in temp_feeding_flies]
            ### Then, join these two lists.
            flies_in_order=temp_feeding_flies+temp_non_feeding_flies

            ### Now, plot each fly as a row, and plot each feed as a colored raster for every fly.
            flycount=int(len(flies_in_order))
            for k, flyid in enumerate(flies_in_order):
                tt=tempfeeds[tempfeeds.FlyID==flyid]
                for idx in [idx for idx in tt.index if ~_np.isnan(tt.loc[idx,'FeedDuration_s'])]:
                    rasterplot_kwargs=dict(xmin=tt.loc[idx,'RelativeTime_s'],
                                           xmax=tt.loc[idx,'RelativeTime_s']+tt.loc[idx,'FeedDuration_s'],

                                           ymin=(1/maxflycount)*(maxflycount-k-1),
                                           ymax=(1/maxflycount)*(maxflycount-k),

                                           color=palette[ tt.loc[idx,color_by] ],
                                           label="_"*k + tt.loc[idx,color_by],

                                           alpha=0.8)

                    rasterax.axvspan(**rasterplot_kwargs)

                ### Plot the flyid labels if so desired.
                if add_flyid_labels:
                    if flyid in temp_non_feeding_flies:
                        label_color='grey'
                    else:
                        label_color='black'
                    rasterax.text(-85, (1/maxflycount)*(maxflycount-k-1) + (1/maxflycount)*.5,
                                flyid,
                                color=label_color,
                                verticalalignment='center',
                                horizontalalignment='right',
                                fontsize=8)
            ## Aesthetic tweaks
            rasterax.yaxis.set_visible(False)
            rasterax.set_title(grp)

            ### Format x-axis.
            _plot_helpers.format_timecourse_xaxis(rasterax)

        ## Despine accordingly (if multiple axes were produced.)
        ## Note the we remove the left spine (set to True).
        if len(groupby_grps)>1:
            for a in axx:
                _sns.despine(ax=a,left=True,trim=True,offset=5)
        else:
            _sns.despine(ax=axx,left=True,trim=True,offset=5)

        # Position the raster color legend.
        if num_plots>1:
            rasterlegend_ax=axx
        else:
            rasterlegend_ax=[ axx ]

        for a in rasterlegend_ax:
            a.legend(loc='upper left',bbox_to_anchor=(0,-0.15),
                     handles=raster_legend_handles)

        # End and return the figure.
        if ax is None:
            return axx

    #####  ###### #####   ####  ###### #    # #####    ###### ###### ###### #####  # #    #  ####
    #    # #      #    # #    # #      ##   #   #      #      #      #      #    # # ##   # #    #
    #    # #####  #    # #      #####  # #  #   #      #####  #####  #####  #    # # # #  # #
    #####  #      #####  #      #      #  # #   #      #      #      #      #    # # #  # # #  ###
    #      #      #   #  #    # #      #   ##   #      #      #      #      #    # # #   ## #    #
    #      ###### #    #  ####  ###### #    #   #      #      ###### ###### #####  # #    #  ####

    def percent_feeding(self,group_by='Genotype',
                        time_start=0,time_end=360,
                        palette_type='categorical'):
        """
        Produces a lineplot depicting the percent of flies feeding for each condition.
        A 95% confidence interval for each proportion of flies feeding is also given.

        Keywords
        --------
        group_by: string, default 'Genotype'
            The column or label indicating the categorical grouping on the x-axis.

        time_start, time_end: integer, default 0 and 360 respectively
            The time window (in minutes) during which to compute and display the
            percent flies feeding.

        palette_type: string, 'categorical' or 'sequential'.

        Returns
        -------
        A matplotlib Axes instance, and a pandas DataFrame with the statistics.
        """
        # Get plotting variables.
        percent_feeding_summary=_plot_helpers.compute_percent_feeding(self._experiment.flies,
                                                             self._experiment.feeds,
                                                             group_by,
                                                             start=time_start,
                                                             end=time_end)


        cilow=percent_feeding_summary.ci_lower.tolist()
        cihigh=percent_feeding_summary.ci_upper.tolist()
        ydata=percent_feeding_summary.percent_feeding.tolist()

        # Select palette.
        if palette_type=='categorical':
            color_palette=_plot_helpers._make_categorial_palette(self._experiment.feeds,group_by)
        elif palette_type=='sequential':
            color_palette=_plot_helpers._make_sequential_palette(self._experiment.feeds,group_by)

        # Set style.
        _sns.set(style='ticks',context='talk',font_scale=1.1)

        # Initialise figure.
        f,ax=_plt.subplots(1,figsize=(8,5))
        ax.set_ylim(0,110)
        # Plot 95CI first.
        ax.fill_between(range(0,len(percent_feeding_summary)),
                        cilow,cihigh,
                        alpha=0.25,
                        color='grey' )
        # Then plot the line.
        percent_feeding_summary.percent_feeding.plot.line(ax=ax,color='k',lw=1.2)

        for j,s in enumerate(ydata):
            ax.plot(j, s, 'o',
                    color=color_palette[j])

        # Aesthetic tweaks.
        ax.xaxis.set_ticks( [i for i in range( 0,len(percent_feeding_summary) )] )
        ax.xaxis.set_ticklabels( percent_feeding_summary.index.tolist() )

        xmax=ax.xaxis.get_ticklocs()[-1]
        ax.set_xlim(-0.2, xmax+0.2) # Add x-padding.
        _bsc.rotate_ticks(ax, angle=45, alignment='right')
        _sns.despine(ax=ax,trim=True,offset={'left':1})
        ax.set_ylabel('Percent Feeding')

        f.tight_layout()
        return f, percent_feeding_summary