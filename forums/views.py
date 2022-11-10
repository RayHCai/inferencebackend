from rest_framework.views import APIView
from rest_framework.response import Response

from inferencebackend.utils import forum_csv_to_array, forum_csv_to_df

from forums.models import Forums
from forums.forms import ForumPostsForm

class ForumsView(APIView):
    def get(self, request):
        '''
        Get forum object from ID or get all forum objects

        Request parameters
            - forum_id (optional) -> id of forum object to retrieve
        '''

        forum_id = request.GET.get('forum_id')

        if not forum_id: # if the request doesn't have a forum id
            serialized_forums = []

            for forum in Forums.objects.all():
                serialized_forums.append(
                    {
                        'id': str(forum.id),
                        'name': forum.get_file_name()
                    }
                )

            return Response(
                {
                    'message': 'Successfuly fetched all forums', 
                    'data': serialized_forums
                }, 
                status=200
            )
        else:
            try:
                forum = Forums.objects.get(id=forum_id)

                serialized_forum = {
                    'id': str(forum.id),
                    'name': forum.get_file_name(),
                    'posts': forum_csv_to_array(forum)
                }

                return Response(
                    {
                        'message': 'Successfuly fetched forum',
                        'data': serialized_forum
                    }, 
                    status=200
                )
            except Forums.DoesNotExist:
                return Response({'message': 'Forum does not exist'}, status=404)

    def post(self, request):
        '''
        Create forum object from CSV file

        Request data
            - file -> CSV file for forum
        '''

        csv_file = request.data.get('file')

        if not csv_file:
            return Response({'message': 'Invalid request data'}, status=400)

        forum = Forums.objects.create(csv_file=csv_file)

        return Response(
            {
                'message': 'Successfuly created forum', 
                'data': str(forum.id)
            }, 
            status=200
        )

class ForumPostsView(APIView):
    def get(self, request):
        '''
        Get specific post information from post id and forum id

        Request parameters
            - post_id -> ID of post
            - forum_id -> ID of forum
        '''

        forum_posts_form = ForumPostsForm(request.GET)

        if not forum_posts_form.is_valid():
            return Response({'message': 'Invalid request data'}, status=400)

        try:
            forum_id = forum_posts_form.cleaned_data.get('forum_id')

            forum_obj = Forums.objects.get(id=forum_id)
        except Forums.DoesNotExist:
            return Response({'message': 'Forums does not exist'}, status=404)
        
        forum_df = forum_csv_to_df(forum_obj)

        post = forum_df.loc[
            forum_df.get('id') == int(
                forum_posts_form.cleaned_data.get('post_id')
            )
        ]

        post_dict = {
            'post_id': int(post.iloc[0, 0]),
            'user_id': int(post.iloc[0, 1]),
            'user_full_name': post.iloc[0, 2],
            'message': post.iloc[0, 3]
        }

        return Response(
            {
                'message': 'Successfuly retrieved post', 
                'data': post_dict
            }, 
            status=200
        )
