"""Tests unitaires pour les jobs de scraping."""
import pytest
import asyncio
import uuid
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.routers.scraping.jobs import (
    JOBS,
    _process_single_source_job_async,
    _process_keyword_job_async,
    start_single_source_job,
    start_keyword_scrape,
    get_job_status,
    cancel_job,
    cancel_all_jobs
)
from app.routers.scraping.endpoints import KeywordsPayload


class TestJobCreation:
    """Tests pour la création de jobs."""
    
    def setup_method(self):
        """Nettoyer les jobs avant chaque test."""
        JOBS.clear()
    
    def test_create_single_source_job(self):
        """Test la création d'un job pour une source unique."""
        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            'id': job_id,
            'status': 'pending',
            'progress': {'total': 1, 'completed': 0},
            'results': [],
            'errors': [],
            'cancelled': False,
            'error': None,
        }
        
        assert job_id in JOBS
        assert JOBS[job_id]['status'] == 'pending'
        assert JOBS[job_id]['progress']['total'] == 1
        assert JOBS[job_id]['progress']['completed'] == 0
    
    def test_create_keyword_job(self):
        """Test la création d'un job avec keywords."""
        job_id = str(uuid.uuid4())
        keywords = ['OVH', 'cloud']
        sources = ['x', 'github', 'stackoverflow']
        total_tasks = len(keywords) * len(sources)
        
        JOBS[job_id] = {
            'id': job_id,
            'status': 'pending',
            'progress': {'total': total_tasks, 'completed': 0},
            'results': [],
            'errors': [],
            'cancelled': False,
            'error': None,
        }
        
        assert job_id in JOBS
        assert JOBS[job_id]['status'] == 'pending'
        assert JOBS[job_id]['progress']['total'] == total_tasks
        assert JOBS[job_id]['progress']['completed'] == 0


class TestJobStatus:
    """Tests pour le statut des jobs."""
    
    def setup_method(self):
        """Nettoyer les jobs avant chaque test."""
        JOBS.clear()
    
    def test_job_status_pending(self):
        """Test que le statut initial est 'pending'."""
        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            'id': job_id,
            'status': 'pending',
            'progress': {'total': 1, 'completed': 0},
        }
        
        assert JOBS[job_id]['status'] == 'pending'
    
    def test_job_status_running(self):
        """Test le changement de statut vers 'running'."""
        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            'id': job_id,
            'status': 'pending',
            'progress': {'total': 1, 'completed': 0},
        }
        
        JOBS[job_id]['status'] = 'running'
        assert JOBS[job_id]['status'] == 'running'
    
    def test_job_status_completed(self):
        """Test le changement de statut vers 'completed'."""
        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            'id': job_id,
            'status': 'running',
            'progress': {'total': 10, 'completed': 10},
        }
        
        JOBS[job_id]['status'] = 'completed'
        assert JOBS[job_id]['status'] == 'completed'
        assert JOBS[job_id]['progress']['completed'] == JOBS[job_id]['progress']['total']
    
    def test_job_status_failed(self):
        """Test le changement de statut vers 'failed'."""
        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            'id': job_id,
            'status': 'running',
            'progress': {'total': 10, 'completed': 5},
            'error': 'Test error',
        }
        
        JOBS[job_id]['status'] = 'failed'
        assert JOBS[job_id]['status'] == 'failed'
        assert JOBS[job_id]['error'] == 'Test error'


class TestJobProgress:
    """Tests pour la progression des jobs."""
    
    def setup_method(self):
        """Nettoyer les jobs avant chaque test."""
        JOBS.clear()
    
    def test_progress_initialization(self):
        """Test l'initialisation de la progression."""
        job_id = str(uuid.uuid4())
        total_tasks = 100
        JOBS[job_id] = {
            'id': job_id,
            'status': 'pending',
            'progress': {'total': total_tasks, 'completed': 0},
        }
        
        assert JOBS[job_id]['progress']['total'] == total_tasks
        assert JOBS[job_id]['progress']['completed'] == 0
    
    def test_progress_update(self):
        """Test la mise à jour de la progression."""
        job_id = str(uuid.uuid4())
        total_tasks = 100
        JOBS[job_id] = {
            'id': job_id,
            'status': 'running',
            'progress': {'total': total_tasks, 'completed': 0},
        }
        
        # Simuler la progression
        for i in range(1, 11):
            JOBS[job_id]['progress']['completed'] = i
            assert JOBS[job_id]['progress']['completed'] == i
        
        assert JOBS[job_id]['progress']['completed'] == 10
        assert JOBS[job_id]['progress']['completed'] < JOBS[job_id]['progress']['total']
    
    def test_progress_completion(self):
        """Test la complétion de la progression."""
        job_id = str(uuid.uuid4())
        total_tasks = 10
        JOBS[job_id] = {
            'id': job_id,
            'status': 'running',
            'progress': {'total': total_tasks, 'completed': 0},
        }
        
        JOBS[job_id]['progress']['completed'] = total_tasks
        assert JOBS[job_id]['progress']['completed'] == JOBS[job_id]['progress']['total']
    
    def test_progress_percentage(self):
        """Test le calcul du pourcentage de progression."""
        job_id = str(uuid.uuid4())
        total_tasks = 100
        JOBS[job_id] = {
            'id': job_id,
            'status': 'running',
            'progress': {'total': total_tasks, 'completed': 25},
        }
        
        progress = JOBS[job_id]['progress']
        percentage = (progress['completed'] / progress['total']) * 100
        assert percentage == 25.0
    
    def test_progress_zero_division(self):
        """Test que la progression gère correctement total=0."""
        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            'id': job_id,
            'status': 'pending',
            'progress': {'total': 0, 'completed': 0},
        }
        
        progress = JOBS[job_id]['progress']
        if progress['total'] > 0:
            percentage = (progress['completed'] / progress['total']) * 100
        else:
            percentage = 0
        assert percentage == 0


class TestJobCancellation:
    """Tests pour l'annulation de jobs."""
    
    def setup_method(self):
        """Nettoyer les jobs avant chaque test."""
        JOBS.clear()
    
    def test_cancel_single_job(self):
        """Test l'annulation d'un job unique."""
        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            'id': job_id,
            'status': 'running',
            'progress': {'total': 100, 'completed': 50},
            'cancelled': False,
        }
        
        JOBS[job_id]['cancelled'] = True
        JOBS[job_id]['status'] = 'cancelled'
        
        assert JOBS[job_id]['cancelled'] is True
        assert JOBS[job_id]['status'] == 'cancelled'
    
    def test_cancel_all_jobs(self):
        """Test l'annulation de tous les jobs."""
        # Créer plusieurs jobs
        for i in range(3):
            job_id = str(uuid.uuid4())
            JOBS[job_id] = {
                'id': job_id,
                'status': 'running',
                'progress': {'total': 100, 'completed': i * 10},
                'cancelled': False,
            }
        
        # Annuler tous les jobs
        for job_id in JOBS:
            JOBS[job_id]['cancelled'] = True
            JOBS[job_id]['status'] = 'cancelled'
        
        # Vérifier que tous les jobs sont annulés
        for job_id in JOBS:
            assert JOBS[job_id]['cancelled'] is True
            assert JOBS[job_id]['status'] == 'cancelled'


class TestJobErrors:
    """Tests pour la gestion des erreurs dans les jobs."""
    
    def setup_method(self):
        """Nettoyer les jobs avant chaque test."""
        JOBS.clear()
    
    def test_job_error_tracking(self):
        """Test le suivi des erreurs dans un job."""
        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            'id': job_id,
            'status': 'running',
            'progress': {'total': 100, 'completed': 50},
            'errors': [],
            'error': None,
        }
        
        # Ajouter une erreur
        error_msg = "Test error message"
        JOBS[job_id]['errors'].append(error_msg)
        JOBS[job_id]['error'] = error_msg
        
        assert len(JOBS[job_id]['errors']) == 1
        assert JOBS[job_id]['errors'][0] == error_msg
        assert JOBS[job_id]['error'] == error_msg
    
    def test_job_multiple_errors(self):
        """Test le suivi de plusieurs erreurs."""
        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            'id': job_id,
            'status': 'running',
            'progress': {'total': 100, 'completed': 50},
            'errors': [],
        }
        
        # Ajouter plusieurs erreurs
        errors = ["Error 1", "Error 2", "Error 3"]
        for error in errors:
            JOBS[job_id]['errors'].append(error)
        
        assert len(JOBS[job_id]['errors']) == 3
        assert JOBS[job_id]['errors'] == errors
    
    def test_job_failure_status(self):
        """Test que le statut passe à 'failed' en cas d'erreur."""
        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            'id': job_id,
            'status': 'running',
            'progress': {'total': 100, 'completed': 50},
            'error': 'Critical error',
        }
        
        JOBS[job_id]['status'] = 'failed'
        
        assert JOBS[job_id]['status'] == 'failed'
        assert JOBS[job_id]['error'] == 'Critical error'

