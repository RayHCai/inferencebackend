import pandas as pd

from forums.models import Forums

def forum_csv_to_df(forum_obj: Forums):
    '''
    Convert forum CSV file to pandas dataframe

    Parameters
        - forum_obj: Forum
    
    Returns
        - pandas DataFrame
            - id
            - userid
            - userfullname
            - message
    '''

    forum = pd.read_csv(forum_obj.csv_file)

    # only need these columns
    needed_columns = [
        'id', 
        'userid', 
        'userfullname', 
        'message'
    ]

    # drop all comments and only keep needed columns
    forum = forum.loc[forum.get('parent') == 0][needed_columns]

    # need to normalize whitespace characters
    forum['message'] = (forum['message']
        .str
        .split()
        .str
        .join(' ')
    ) 

    return forum

def forum_csv_to_array(forum_obj: Forums):
    '''
    Convert forum CSV file to a dictionary

    Parameters
        - forum_obj: Forum
    
    Returns:
        - list of dictionaries
            - id
            - user_id
            - user_full_name
            - message
    '''

    forum = forum_csv_to_df(forum_obj) # convert CSV to dataframe

    forum_posts = []

    for post in forum.itertuples():
        forum_posts.append(
            {
                'id': post.id,
                'user_id': post.userid,
                'user_full_name': post.userfullname,
                'message': post.message
            }
        )

    return forum_posts
