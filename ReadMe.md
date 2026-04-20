## Files Details

1. A_star.py
2. A_star2.py
These two serve as paractice files to have grip and understanding over algorithm's working

Go through files flow wise
---
1. db.py
    This files connect to your mongo db client
    Change local url to your atlas connection string if your are mongo atlas instead of mongo compass
    Setup your mongo db
    create a collection named "marketing_ai"
    
    load_dataset_from_kaggle()
        1. this read the .csv dataset 
        2. preprocess its required columns as per our need
        3. insert the records into mongo db  

2. channel_profile.py

    This file contain a data class named "ChannelProfile"
    Channel Profile's attribute define a channel's profile at given node in search tree
    
    build_channel_profile(db) returns dictionary (key:name_of_channel, value:profile)
    It reduce the dataset's information into one channel's profile by aggeragating its
    information into averages and standard deviations
    to understand mongo_db pipeline recall aggeragate columns functions and group by from SQL Database Lab

3. search_node.py

    Contains simple node of the search tree with all its other attributes set (compare=False)
    because we will only compare its f value to selecting while searching
    f is negative to get maximum value from a min_heap

4. algo.py

    contains two core methods of the roi_engine
    compute_heruistic()
        1. calculated remaining budget
        2. filter out all eligible not_visited nodes in candinates : list [ChannelProfile]
        3. sort out candinates in descending order based on roi_per_dollar (roi_per_dollar is property in ChannelProfile)
        4. set h_value to 0.0
        5. loop over all candinates list
            while we have enough budget
            cummulate the roi of all channels in candinates list starting from best (it is sorted)
            when budget exhuast
            add fraction of roi of next best available channel in candinates
        6. return the h_value

    a_star()
        to be implemented

5. main.py

    main file where we use apply our algorithm
    later this may be used to run our flask server for web app