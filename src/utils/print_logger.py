import sys
import os
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

class PrintLogger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PrintLogger, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        # Create logs directory in user's home directory
        home_dir = str(Path.home())
        log_dir = os.path.join(home_dir, '.egangotri_logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Set up rotating file handler (10MB max size)
        log_file = os.path.join(log_dir, 'egangotri_print.log')
        self.logger = logging.getLogger('PrintLogger')
        self.logger.setLevel(logging.INFO)
        
        handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=1,
            encoding='utf-8'
        )
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Store original stdout
        self.original_stdout = sys.stdout
        
        # Create custom stdout
        class CustomStdout:
            def __init__(self, logger, original_stdout):
                self.logger = logger
                self.original_stdout = original_stdout
            
            def write(self, text):
                if text.strip():  # Only log non-empty strings
                    ascii_text = (text.strip()
                        .replace('├', '+')
                        .replace('└', '\\')
                        .replace('─', '-'))
                    try:
                        self.logger.info(ascii_text)
                    except UnicodeEncodeError:
                        # If still getting encode errors, force encode to ASCII
                        self.logger.info(ascii_text.encode('ascii', 'replace').decode())
                self.original_stdout.write(text)
            
            def flush(self):
                self.original_stdout.flush()
        
        # Replace sys.stdout with custom stdout
        sys.stdout = CustomStdout(self.logger, self.original_stdout)
    
    @classmethod
    def restore_stdout(cls):
        """Restore the original stdout if needed"""
        if cls._instance and hasattr(cls._instance, 'original_stdout'):
            sys.stdout = cls._instance.original_stdout
