from rest_framework.views import APIView
from rest_framework.response import Response

from inferencebackend.test_utils import forum_csv_to_array, forum_csv_to_df

from forums.models import Forums

class ForumsView(APIView):
    def get(self, request):
        '''
        Get forum object from ID or get all forum objects

        Request parameters
            - forum_id (optional) -> id of forum object to retrieve
        '''

        if not request.GET.get('forum_id'): # if the request doesn't have a forum id
            all_forums_serialized = []

            for forum in Forums.objects.all():
                all_forums_serialized.append(
                    {
                        'id': str(forum.id),
                        'name': forum.get_file_name()
                    }
                )

            return Response(
                {
                    'message': 'Successfuly fetched forums', 
                    'data': all_forums_serialized
                }, 
                status=200
            )    
        else:
            try:
                forum_obj = Forums.objects.get(
                    id=request.GET.get('forum_id')
                ) 

                data = {
                    'id': str(forum_obj.id),
                    'name': forum_obj.get_file_name(),
                    'posts': forum_csv_to_array(forum_obj)
                }

                return Response(
                    {
                        'message': 'Successfuly fetched forum',
                        'data': data
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

        if not request.data.get('file'):
            return Response({'message': 'Invalid request data'}, status=400)

        f = Forums.objects.create(csv_file=request.data.get('file'))

        return Response({'message': 'Successfuly created forum', 'data': str(f.id)}, status=200)

class ForumPostsView(APIView):
    def get(self, request):
        '''
        Get specific post information from post id and forum id

        Request parameters
            - post_id -> ID of post
            - forum_id -> ID of forum
        '''

        if not request.GET.get('post_id') or not request.GET.get('forum_id'):
            return Response({'message': 'Invalid request data'}, status=400)

        try:
            forum_obj = Forums.objects.get(id=request.GET.get('forum_id'))
        except Forums.DoesNotExist:
            return Response({'message': 'Forums does not exist'}, status=404)
        
        forum = forum_csv_to_df(forum_obj)

        post = forum.loc[forum.get('id') == int(request.GET.get('post_id'))]

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
