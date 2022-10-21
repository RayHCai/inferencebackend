import json
import multiprocessing

import numpy as np

from rest_framework.views import APIView
from rest_framework.response import Response

from transformers import pipeline
from sentence_transformers import SentenceTransformer, util

from forums.models import Forums
from foruminferences.models import ForumInferences
from foruminferences.forms import PostRelationsForm

from inferencebackend.test_utils import forum_csv_to_df
from inferencebackend.settings import INFERENCES_FILE_LOCATION

def cosine_similarity(vec1, vec2):
    from numpy.linalg import norm
        # cosine_similarity = (
        #     np.dot(base_answer.get('answer_embedding'), answer_embedding) / 
        #     (
        #         norm(base_answer.get('answer_embedding')) * norm(answer_embedding)
        #     )
        # )

    return util.pytorch_cos_sim(vec1, vec2).tolist()[0][0]

class InferencesView(APIView):
    def get(self, request):
        '''
        Get inference files for forum

        Request parameters
            - forum_id -> id of forum to get inferences for
        '''

        if not request.GET.get('forum_id'):
            return Response({'message': 'Invalid response data'}, status=400)

        try:
            forum_obj = Forums.objects.get(id=request.GET.get('forum_id'))
        except Forums.DoesNotExist:
            return Response({'message': 'Forum does not exist'}, status=404)

        if not (forum_inferences := ForumInferences.objects.filter(forum=forum_obj).first()):
            return Response({'message': 'No inferences exist for forum'}, status=404)

        with open(f'{INFERENCES_FILE_LOCATION}{forum_inferences.inferences.name}') as inferences:
            inference_dict = json.loads(inferences.read())

            return Response(
                {
                    'message': 'Successfuly retrieved inferences', 
                    'data': inference_dict
                }, 
                status=200
            )

    def post(self, request):
        '''
        Create inferences for forum

        Request body
            - forum_id -> id of the forum to make inferences on
            - questions -> list of questions
        '''
        
        if not request.data.get('forum_id') or not request.data.get('questions'):
            return Response({'message': 'Invalid request data'}, status=400)

        try:
            forum_obj = Forums.objects.get(id=request.data.get('forum_id'))
        except Forums.DoesNotExist:
            return Response({'message': 'Forum does not exist'}, status=404)

        if ForumInferences.objects.filter(forum=forum_obj).exists():
            return Response({'message': 'An inference already exists for this forum'}, status=400)

        questions = request.data.get('questions')

        num_cores = multiprocessing.cpu_count()

        # ------ Data Prep ------ #

        forum = forum_csv_to_df(forum_obj)

        # ------ Inferences ------ #

        qa_model_name = 'deepset/roberta-base-squad2' # for answer inferences
        sent_model_name = 'all-mpnet-base-v2' # for answer embeddings

        qa_model = pipeline(
            'question-answering', 
            model=qa_model_name, 
            tokenizer=qa_model_name
        )

        sent_model = SentenceTransformer(sent_model_name)
        
        inferences = {}

        for post in forum.itertuples(): # iterate through each post
            post_answers = []

            for question in questions: # then each question
                # model requires question and context
                qa_model_input = {
                    'question': question,
                    'context': post.message
                }
                
                qa_result = qa_model(
                    qa_model_input, 
                    num_workers=num_cores - 1
                )

                # create an embedding for the answer
                answer_embedding = sent_model.encode(qa_result['answer']) 

                post_answers.append({
                    'answer': qa_result['answer'],
                    'start_ind': qa_result['start'], # start index of the answer
                    'end_ind': qa_result['end'], # end index of the answer,
                    'answer_embedding': answer_embedding.tolist() # need to convert to list so it is JSON serializable
                })

            inferences[post.id] = post_answers

        full_data = {
            'questions': questions,
            'inferences': inferences
        }

        forum_file_name = forum_obj.get_file_name()

        inference_file_name = f'{forum_file_name}_inferences.json'

        open(f'{INFERENCES_FILE_LOCATION}{inference_file_name}', 'x') # create inference file

        with open(f'{INFERENCES_FILE_LOCATION}{inference_file_name}', 'w') as forum_inference:
            forum_inference.write(
                json.dumps(full_data)
            )
        
        ForumInferences.objects.create(
            forum=forum_obj, 
            inferences=inference_file_name
        )

        return Response(
            {
                'message': 'Successfuly made inferences', 
                'data': full_data
            }, 
            status=200
        )

class PostRelationsView(APIView):
    def post(self, request):
        '''
        Make a list of forum posts with cosine similarity greater than 0.5 (for a given quesiton)

        Request body
            - question -> question to filter by
            - forum_id -> id for forum to be used
            - post_id -> id for post to be used as a baseline
        '''
        
        post_relations_form = PostRelationsForm(request.data)

        if not post_relations_form.is_valid():
            return Response({'message': 'Invalid request data'}, status=400)

        try:
            forum_obj = Forums.objects.get(
                id=post_relations_form.cleaned_data.get('forum_id')
            )
        except Forums.DoesNotExist:
            return Response({'message': 'Forum does not exist'}, status=404)
        
        try:
            forum_inferences = ForumInferences.objects.get(forum=forum_obj)
        except ForumInferences.DoesNotExist:
            return Response({'message': 'Inferences do not exist for forum'}, status=404)
        
        inferences = {}

        with open(f'{INFERENCES_FILE_LOCATION}{forum_inferences.inferences.name}') as inference_file:
            inferences = json.loads(inference_file.read())
        
        # if not inferences were made for given question
        if not post_relations_form.cleaned_data.get('question') in inferences.get('questions'):
            return Response({'message': 'Question does not exist in inferences'}, status=404)

        filtered_inferences = {}

        question_ind = inferences.get('questions').index(post_relations_form.cleaned_data.get('question'))

        if not (base_inference := (
                inferences
                .get('inferences')
                .get(
                    str(post_relations_form.cleaned_data.get('post_id'))
                )
            )
        ): return Response({'message': 'Post ID does not exist on forum'}, status=404)

        base_answer = base_inference[question_ind]

        for post_id, answers in inferences.get('inferences').items():
            answer_embedding = answers[question_ind].get('answer_embedding')

            answers_cosine_similarity = cosine_similarity(base_answer.get('answer_embedding'), answer_embedding)

            if answers_cosine_similarity > 0.5:
                filtered_inferences[post_id] = {
                    'post_id': post_id,
                    'similarity': answers_cosine_similarity
                }

        return Response(
            {
                'message': 'Successfuly grouped inferences', 
                'data': filtered_inferences
            }, 
            status=200
        )
