import json
import os

from rest_framework.views import APIView
from rest_framework.response import Response

from inferencebackend.utils import forum_csv_to_df
from inferencebackend.settings import INFERENCES_FILE_LOCATION, NUM_CORES, QA_MODEL_NAME, SENT_MODEL_NAME

from forums.models import Forums

from foruminferences.models import ForumInferences
from foruminferences.forms import PostRelationsForm

from transformers import pipeline
from sentence_transformers import SentenceTransformer, util

def cosine_similarity(vec1, vec2):
    '''
    Calculate cosine similarity between two sentence embeddings

    Args:
        vec1: Embedding of first sentence
        vec2: Embedding of second sentence

    Returns:
        Similarity between two sentence vectors (float)
    '''

    return util.pytorch_cos_sim(vec1, vec2).tolist()[0][0]

def make_inferences(qa_model, sent_model, question, context):
    '''
    Make inferences for a question given a context

    Args:
        qa_model: pipeline
        sent_model: SentenceTransformer
        question: string
        context: string
    
    Returns:
        Object with results for inferences
            - answer: answer to given question
            - start_ind: start index of the answer
            - end_ind: end index of the answer 
            - answer_embedding: list version of embedding for the answer
    '''

    # qa model requires question and context
    qa_model_input = {
        'question': question,
        'context': context
    }
    
    qa_result = qa_model(
        qa_model_input, 
        num_workers=NUM_CORES - 1
    )

    # create an embedding for the answer
    answer_embedding = sent_model.encode(qa_result['answer']) 

    return {
        'answer': qa_result['answer'],
        'start_ind': qa_result['start'],
        'end_ind': qa_result['end'],
        'answer_embedding': answer_embedding.tolist()
    }

class InferencesView(APIView):
    def get(self, request):
        '''
        Get inference files for forum

        Request parameters
            - forum_id -> id of forum to get inferences for
        '''

        forum_id = request.GET.get('forum_id')

        if not forum_id:
            return Response({'message': 'Invalid response data'}, status=400)

        try:
            forum_obj = Forums.objects.get(id=forum_id)
        except Forums.DoesNotExist:
            return Response({'message': 'Forum does not exist'}, status=404)

        # if there are no inferences for forum object
        if not (
            forum_inferences := ForumInferences.objects.filter(forum=forum_obj).first()
        ):
            return Response({'message': 'No inferences exist for forum'}, status=404)

        with open(INFERENCES_FILE_LOCATION + forum_inferences.inferences.name) as inference_file:
            inference_dict = json.loads(inference_file.read())

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

        forum_id = request.data.get('forum_id')
        questions = request.data.get('questions')
        
        if not forum_id or not questions:
            return Response({'message': 'Invalid request data'}, status=400)

        try:
            forum_obj = Forums.objects.get(id=forum_id)
        except Forums.DoesNotExist:
            return Response({'message': 'Forum does not exist'}, status=404)

        if ForumInferences.objects.filter(forum=forum_obj).exists():
            return Response({'message': 'An inference already exists for this forum'}, status=400)

        forum_df = forum_csv_to_df(forum_obj)

        # Make Inferences

        qa_model = pipeline(
            'question-answering', 
            model=QA_MODEL_NAME, 
            tokenizer=QA_MODEL_NAME
        )

        sent_model = SentenceTransformer(SENT_MODEL_NAME)
        
        inferences = {}

        for post in forum_df.itertuples(): # iterate through each post
            post_answers = []

            for question in questions: # then each question
                post_answers.append(
                    make_inferences(
                        qa_model, 
                        sent_model, 
                        question, 
                        post.message
                    )
                )

            inferences[post.id] = post_answers

        full_data = {
            'questions': questions,
            'inferences': inferences
        }

        forum_file_name = forum_obj.get_file_name()

        inference_file_name = f'{forum_file_name}_inferences.json'
        inference_file_location = INFERENCES_FILE_LOCATION + inference_file_name

        open(inference_file_location, 'x') # create inference file

        with open(inference_file_location, 'w') as forum_inference:
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
        Make a list of forum posts with cosine similarity greater than user input (for a given quesiton)

        Request body
            - question -> question to filter by
            - forum_id -> id for forum to be used
            - post_id -> id for post to be used as a baseline
            - similarity -> the cosine similarity baseline for similar posts
        '''
        
        post_relations_form = PostRelationsForm(request.data)

        if not post_relations_form.is_valid():
            return Response({'message': 'Invalid request data'}, status=400)

        try:
            forum_id = post_relations_form.cleaned_data.get('forum_id')

            forum_obj = Forums.objects.get(
                id=forum_id
            )
        except Forums.DoesNotExist:
            return Response({'message': 'Forum does not exist'}, status=404)
        
        try:
            forum_inferences = ForumInferences.objects.get(forum=forum_obj)
        except ForumInferences.DoesNotExist:
            return Response({'message': 'Inferences do not exist for forum'}, status=404)
        
        inferences = {}

        with open(INFERENCES_FILE_LOCATION + forum_inferences.inferences.name) as inference_file:
            inferences = json.loads(inference_file.read())
        
        question = post_relations_form.cleaned_data.get('question')
        inferenced_questions = inferences.get('questions')
        inferences_dict = inferences.get('inferences')

        # if no inferences were made for given question
        if not question in inferenced_questions:
            return Response({'message': 'No inferences were made for question'}, status=404)

        filtered_inferences = {}

        question_ind = inferenced_questions.index(question)

        post_id = str(post_relations_form.cleaned_data.get('post_id'))

        if not (
            base_inference := inferences_dict.get(post_id)
        ): 
            return Response({'message': 'Post ID does not exist on forum'}, status=404)

        base_answer = base_inference[question_ind]

        base_similarity = post_relations_form.cleaned_data.get('similarity')

        for post_id, answers in inferences_dict.items():
            answer_embedding = answers[question_ind].get('answer_embedding')
            
            answers_cosine_similarity = cosine_similarity(
                base_answer.get('answer_embedding'), 
                answer_embedding
            )

            if answers_cosine_similarity > base_similarity:
                filtered_inferences[post_id] = {
                    'post_id': post_id,
                    'similarity': answers_cosine_similarity
                }

        return Response(
            {
                'message': 'Successfuly grouped posts', 
                'data': filtered_inferences
            }, 
            status=200
        )

class QuestionInferenceView(APIView):
    def post(self, request):
        forum_id = request.data.get('forum_id')
        question = request.data.get('question')
        post_ids = request.data.get('post_ids')

        if not forum_id or not question or not post_ids:
            return Response({'message': 'Invalid request data'}, status=400)

        try:
            forum_obj = Forums.objects.get(id=forum_id)
        except Forums.DoesNotExist:
            return Response({'message': 'Forum does not exist'}, status=404)

        forum = forum_csv_to_df(forum_obj)

        posts = [post for post in forum.itertuples() if str(post.id) in post_ids]

        # Make inferences

        qa_model = pipeline(
            'question-answering', 
            model=QA_MODEL_NAME, 
            tokenizer=QA_MODEL_NAME
        )

        sent_model = SentenceTransformer(SENT_MODEL_NAME)
        
        inferences = {}

        for post in posts: # iterate through each post
            inferences[post.id] = make_inferences(
                qa_model, 
                sent_model, 
                question, 
                post.message
            )

        full_data = {
            'question': question,
            'inferences': inferences
        }

        return Response(
            {
                'message': 'Successfuly made inferences', 
                'data': full_data
            }, 
            status=200
        )

class DeleteInferencesView(APIView):
    def post(self, request):
        forum_id = request.data.get('forum_id')

        if not forum_id:
            return Response({'message': 'Invalid request data'}, status=400)

        try:
            forum_obj = Forums.objects.get(id=forum_id)
            forum_inferences = ForumInferences.objects.get(forum=forum_obj)

            os.remove(INFERENCES_FILE_LOCATION + forum_inferences.inferences.name)

            forum_inferences.delete()

            return Response({'message': 'Succesfuly deleted inferences'}, status=200)
        except Forums.DoesNotExist:
            return Response({'message': 'Forum does not exist'}, status=404)
        except ForumInferences.DoesNotExist:
            return Response({'message': 'Inferences do not exist for forum'}, status=404)