#!/usr/bin/python
# -*-coding: utf-8 -*-
# Author: Joses Ho
# Email : joseshowh@gmail.com

"""
Package for analysis of ESPRESSO experiments run on CRITTA.
"""



class espresso(object):
    """
    Creates an `espresso` experiment for analysis.

    Supply either a folder with raw feedlog(s) and corresponding metadata
    file(s) in CSV format from CRITTA, or a pre-processed FeedLog DataFrame and
    its corresponding MetaData DataFrame.

    Keywords
    --------
    folder: string
        Path to a folder with at least one FeedLog, along with its corresponding
        MetaData.

    expt_duration_seconds: integer, default None
        If you lack a FeedStats file, enter the experiment duration here,
        in seconds.
    """



    def __init__(self, folder, expt_duration_seconds=None):
        import os

        import numpy as np
        import scipy as sp
        import pandas as pd

        from ._plotter import espresso_plotter as espresso_plotter
        from ._munger import munger as munge

        self.version = '0.3.2'

        allflies= []
        allfeeds= []
        allmetadata= []
        non_feeding_flies= []

        files = os.listdir(folder)
        self.feedlogs = [csv for csv in files
                          if csv.endswith('.csv') and csv.startswith('FeedLog')]
        feedlogs_in_folder = np.array(self.feedlogs)


        # Prepare variables.
        feedlogs_list = list()
        metadata_list = list()
        expt_durations = list()

        # check that each feedlog has a corresponding metadata CSV
        # and feedstat CSV
        for feedlog in feedlogs_in_folder:
            expected_metadata = feedlog.replace('FeedLog','MetaData')
            expected_feedstats = feedlog.replace('FeedLog','FeedStats')
            if expected_metadata not in files:
                raise NameError('A MetaData file for '+feedlog+' cannot be found.\n'+\
                                'MetaData files should start with "MetaData_" and '+\
                                'have the same datetime info as the corresponding FeedLog. Please check.')
            if expected_feedstats not in files:
                if expt_duration_seconds is None:
                    raise ValueError('A FeedStats file for '+feedlog+' cannot be found.\n'+\
                                'FeedStats files should start with "FeedStats_" and '+\
                                'have the same datetime info as the corresponding FeedLog.'
                                ' Alternatively, you can enter `expt_duration_seconds`.')
                else:
                    self.expt_duration_seconds = expt_duration_seconds
            else:
                # Read in all the FeedStats CSV. Identify which FeedStat has the longest
                # recorded experiment duration, and assign that as the overall duration.
                feedstats_in_folder = [f.replace('FeedLog','FeedStats')
                                       for f in feedlogs_in_folder]
                for fs in feedstats_in_folder:
                    fs_path = os.path.join(folder, fs)
                    expt_durations.append(munge.get_expt_duration(fs_path))
                self.expt_duration_seconds = np.max(expt_durations) * 60

        for j, feedlog in enumerate(feedlogs_in_folder):
            datetime_exptname = '_'.join(feedlog.strip('.csv').split('_')[1:3])

            # Read in metadata.
            path_to_metadata = os.path.join(folder,
                                            feedlog.replace('FeedLog',
                                                            'MetaData'))
            metadata_csv = munge.metadata(path_to_metadata)
            metadata_csv['FlyID'] = datetime_exptname + '_Fly' + \
                                    metadata_csv.ID.astype(str)

            # Save the munged metadata.
            metadata_list.append(metadata_csv)
            # Save the fly IDs.
            allflies.append(metadata_csv.loc[:,'FlyID'].copy())

            # Read in feedlog.
            path_to_feedlog = os.path.join(folder,feedlog)
            feedlog_csv = munge.feedlog(path_to_feedlog)
            feedlog_csv.loc[:,'FlyID'] = datetime_exptname + '_Fly' + feedlog_csv.FlyID.astype(str)

            # Detect non-feeding flies, add to the appropriate list.
            non_feeding_flies = non_feeding_flies + munge.detect_non_feeding_flies(metadata_csv,
                feedlog_csv)

            # Define 2 padrows per fly, per food choice (in this case, only one),
            # that will ensure feedlogs for each FlyID fully capture the entire
            # experiment duration.
            feedlog_csv = munge.add_padrows(metadata_csv, feedlog_csv,
                                             self.expt_duration_seconds)
            # Add columns in nanoliters.
            feedlog_csv = munge.compute_nanoliter_cols(feedlog_csv)
            # Add columns for RelativeTime_s and FeedDuration_s.
            feedlog_csv = munge.compute_time_cols(feedlog_csv)

            # Save the munged feedlog.
            feedlogs_list.append(feedlog_csv)


        # Join all processed feedlogs and metadata into respective DataFrames.
        allflies = pd.concat(metadata_list)
        allfeeds = pd.concat(feedlogs_list)
        # # Discard superfluous columns.
        # allfeeds.drop('ID', axis=1, inplace=True)

        # Assign feed choice to the allfeeds DataFrame.
        food_choice_cols = allflies.filter(regex='Tube').columns.tolist()
        food_choice_cols.append('FlyID')

        food_choice_dict = allflies[food_choice_cols]
        food_choice_dict.set_index('FlyID', inplace=True)

        allfeeds['FoodChoice'] = allfeeds.apply(lambda x:
                                    munge.assign_food_choice(x['FlyID'],
                                                         x['ChoiceIdx']+1,
                                                         food_choice_dict),
                                               axis=1)

        # rename columns and types as is appropriate.
        allflies.loc[:,'Genotype'] = allflies.Genotype.str.replace('W','w')
        allflies.loc[:,'Genotype'] = allflies.Genotype.str.replace('iii','111')

        # Assign Status based on genotype.
        allflies['Status'] = pd.Categorical(allflies.Genotype.apply(munge.assign_status_from_genotype),
                                            categories=['Sibling','Offspring'],
                                            ordered=True)


        # Change relevant columns to categorical.
        for col in ['Genotype', 'Temperature', 'Sex']:
            try:
                allflies.loc[:, col] = pd.Categorical(allflies[col],
                                            categories=np.sort(allflies[col].unique()),
                                            ordered=True)
            except KeyError:
                pass
        allfeeds.loc[:, "FoodChoice"] = pd.Categorical(allfeeds.FoodChoice,
                                                    categories=np.sort(allfeeds.FoodChoice.unique()),
                                                    ordered=True)

        # merge metadata with feedlogs.
        print("\nDon't worry about the exception/error below. "
              "It's a harmless pandas bug.")
        allfeeds = pd.merge(allfeeds, allflies,
                            left_on='FlyID', right_on='FlyID')


        # Compute average feed volume per fly in chamber, for each feed.
        allfeeds = munge.average_feed_vol_per_fly(allfeeds)
        # Compute average feed count per fly in chamber, for each feed.
        # This seems redundant, but serves a crucial munging purpose
        # when we are producing timecourse plots.
        allfeeds = munge.average_feed_count_per_fly(allfeeds)
        # Compute average feed speed per fly in chamber, for each feed.
        allfeeds = munge.average_feed_speed_per_fly(allfeeds)

        # Reset the indexes.
        allflies.reset_index(drop=True, inplace=True)
        allfeeds.reset_index(drop=True, inplace=True)

        # Sort by FlyID, then by RelativeTime
        allfeeds.sort_values(['FlyID', 'RelativeTime_s'], inplace=True)

        # Record which flies did not feed.
        allflies['AtLeastOneFeed'] = np.repeat(True,len(allflies))
        non_feeding_flies_idx = allflies[allflies.FlyID.isin(non_feeding_flies)].index
        allflies.loc[non_feeding_flies_idx,'AtLeastOneFeed'] = False


        self.flies = allflies
        self.flies_original_labels = allflies.columns

        self.feeds = allfeeds
        self.feeds_original_labels = allfeeds.columns

        self.feedlog_count = len(feedlogs_in_folder)
        self.genotypes = allflies.Genotype.unique()
        self.temperatures = allflies.Temperature.unique()
        self.sexes = allflies.Sex.unique()
        self.foodtypes = np.unique(allflies.dropna(axis = 1).filter(regex='Tube'))

        # Passes an instance of `self` to plotter.
        self.plot = espresso_plotter.espresso_plotter(self)





    def __repr__(self):
        plural_list = []

        for value in [self.feedlog_count, len(self.genotypes),
                      len(self.temperatures), len(self.foodtypes)]:
            if value > 1:
                plural_list.append('s')
            else:
                plural_list.append('')

        try:
            if len(self.sexes) > 1:
                plural_list.append('s')
            else:
                plural_list.append('')
        except AttributeError:
            pass

        feedlog_summary = "{0} feedlog{1} with ".format(self.feedlog_count,
                                                    plural_list[0]) + \
                          "a total of {} flies.\n".format(len(self.flies))

        genotype_summary = "\n{0} genotype{1} {2}.\n".format(len(self.genotypes),
                                                          plural_list[1],
                                                          self.genotypes)

        temp_summary = "\n{0} temperature{1} {2}.\n".format(len(self.temperatures),
                                                          plural_list[2],
                                                          self.temperatures)

        foodtypes_summary = "\n{0} foodtype{1} {2}.\n".format(len(self.foodtypes),
                                                            plural_list[3],
                                                            self.foodtypes)

        try:
            gender_summary = "\n{0} sex type{1} {2}.\n".format(len(self.sexes),
                                                             plural_list[4],
                                                             self.sexes)
        except AttributeError:
            gender_summary = ''

        try:
            expt_duration_summary = "\nTotal experiment duration = {} minutes\n".format(self.expt_duration_seconds / 60)
        except AttributeError:
            expt_duration_summary = ''

        rep_str = feedlog_summary + genotype_summary + temp_summary + \
                  foodtypes_summary + gender_summary + expt_duration_summary


        if hasattr(self, "added_labels"):
            if len(self.added_labels)>1:
                plural_label = 's have'
            else:
                plural_label = ' has'

            label_summary = "\n{0} label{1} been added: {2}".format(len(self.added_labels),
                                                                plural_label,
                                                                self.added_labels)
            rep_str = rep_str + label_summary

        rep_str = rep_str + '\nESPRESSO v{}'.format(self.version)

        return rep_str





    def __add__(self, other):
        from copy import copy as deepcopy
        import numpy as np
        import pandas as pd
        from ._plotter import espresso_plotter as espresso_plotter

        self_copy = deepcopy(self) # Create a copy of the first espresso object to be summed.
        other_copy = deepcopy(other) # Create a copy of the other espresso object.


        # Merge the flies and feeds attributes.
        print("\nDon't worry about the above exception. "
                      "It's a harmless pandas bug.")
        self_copy.flies = pd.merge(self_copy.flies, other_copy.flies,
            how='outer')
        self_copy.feeds = pd.merge(self_copy.feeds, other_copy.feeds,
            how='outer')
        # carry over the original_labels attrib.
        self_copy.flies_original_labels = self.flies_original_labels
        self_copy.feeds_original_labels = self.feeds_original_labels

        new_labels = []
        for o in [self_copy, other_copy]:
            if hasattr(o, "added_labels"):
                if isinstance(o.added_labels, list):
                    new_labels = new_labels + o.added_labels
                elif isinstance(o.added_labels, str):
                    new_labels.append(o.added_labels)
        new_labels = list( set(new_labels) )
        if len(new_labels)>0:
            self_copy.added_labels = new_labels

        self_copy.feedlogs = list(set(self_copy.feedlogs + other_copy.feedlogs))
        self_copy.feedlog_count = len(self_copy.feedlogs)

        self_copy.genotypes = self_copy.flies.Genotype.unique()
        self_copy.temperatures = self_copy.flies.Temperature.unique()

        self_copy.foodtypes = np.unique(self_copy.flies\
                                        .dropna(axis = 1)\
                                        .filter(regex='Tube'))
        self_copy.plot = espresso_plotter.espresso_plotter(self_copy)

        return self_copy

    def __radd__(self, other):
        if other == 0:
            return self
        else:
            return self.__add__(other)






    def attach_label(self, label_name,
                    label_value = None,
                    label_from_cols = None,
                    sep=','):
        """
        Attach_label a custom label to the metadata and feedlog of an espresso experiment.
        The espresso object is modified in place.

        Keywords
        --------
        label_name: string
            The new category name.

        label_value: default None
            Assigns a custom value to the label for all flies in the espresso experiment.
            You can assign any type of Python object. The label will be converted
            into a pandas Categorical variable.

        label_from_cols: list, default None
            Assigns a value to all flies in this espresso experiment by concatenating
            existing metadata columns of the espresso object. The list order is the
            concatenation order.

        sep: string, default ','
            The seperator used to denote the joined columns if `label_from_cols` is passed.
        """
        import numpy as np

        # Sanity check for keywords passed.
        label_name = str(label_name)

        if label_value is None and label_from_cols is None:
            raise ValueError("Please specify either `label_value` or `label_from_cols`.")
        if label_value is not None and label_from_cols is not None:
            raise ValueError("You have specified both `label_value` or `label_from_cols`. Please only specify one.")
        if label_from_cols is not None and isinstance(label_from_cols, list) is False:
            raise TypeError("`label_from_cols` is not a list. Please check again.")

        if label_value is not None:
            for obj in [self.flies, self.feeds]:
                obj[label_name] = np.repeat(str(label_value), len(obj))
                # turn into Categorical.
                obj.loc[:,label_name] = obj[label_name].astype('category',ordered = True)

        else:
            for col in label_from_cols:
                col = str(col)
                if col not in self.flies.columns:
                    raise KeyError( "{0} is not found in the metadata. Please check.".format(col) )
            for obj in [self.flies, self.feeds]:
                # See https://stackoverflow.com/questions/33098383/merge-multiple-column-values-into-one-column-in-python-pandas
                obj[label_name] = obj[label_from_cols].apply(lambda x: sep.join(x.dropna().astype(str)),axis = 1)
                # turn into Categorical.
                obj.loc[:,label_name] = obj[label_name].astype('category',ordered = True)

        labels=[label_name] # convert to single-member list.
        if hasattr(self, 'added_labels'):
            self.added_labels.extend(labels)
        else:
            self.added_labels = labels

        if label_value is not None:
            print("{0} has been added as a new label, with '{1}' as the custom value.".format(label_name, label_value))
        else:
            print("{0} has been added as a new label. The values were created by concatenating the columns {1}.".format(label_name, label_from_cols))





    def remove_labels(self, labels):
        """
        Removes the label(s) from the `flies` and `feeds` DataFrames of an espresso experiment.
        The espresso experiment is modified in place.

        Keywords
        --------

        labels: string or list.
            A single label to remove, or a list of labels to remove.
        """
        # Sanity checks.
        if 'added_labels' not in self.__dict__:
            raise KeyError('This espresso experimenthas no added labels.')

        # Handle labels depending if string or list.
        if isinstance(labels, str):
            labels = [labels] # convert to single-member list.

        if isinstance(labels,list):
            in_added = [str(l) for l in labels if l in self.added_labels]

            if len(in_added) == 0:
                raise KeyError("Not all labels in {0} is not an added label. Please check.".format(labels))

        self.flies.drop(labels,axis = 1,inplace = True)
        self.feeds.drop(labels,axis = 1,inplace = True)

        # check if we need to remove the added_labels attribute.
        if labels == self.added_labels:
            del self.__dict__['added_labels']
        else:
            for l in labels:
                self.added_labels.remove(l)

        return "{0} has been dropped.".format(labels)


    def remove_all_labels(self):
        """
        Removes add added label(s) from the `flies` and `feeds` DataFrames of an espresso experiment.
        The espresso experiment is modified in place.
        """
        # Sanity checks.
        if 'added_labels' not in self.__dict__:
            raise KeyError('This espresso experiment has no added labels.')

        dropped = self.added_labels

        for attr in [self.flies, self.feeds]:
            attr.drop(dropped,axis = 1,inplace = True)

        del self.__dict__['added_labels']

        return "All added labels {0} have been dropped.".format(dropped)

    def save(self, filename):
        '''Saves the current espresso object as a Python pickle.'''
        import pickle as pk

        with open(filename, 'wb') as f:
            # To ensure compatibility with Py2, set protocol = 2
            pk.dump(self, f, protocol = 2)

def load(filename):
    '''Loads a saved espresso object.'''
    import pickle as pk

    with open(filename, 'rb') as f:
        # Pickle the 'data' dictionary using the highest protocol available.
        out = pk.load(f)

    return out
