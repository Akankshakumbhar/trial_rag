from sqlalchemy import create_engine  # connect your python app to database
from sqlalchemy.ext.declarative import declarative_base # use to create a base class for your database models

from sqlalchemy.orm import sessionmaker #used to craete a session ( connection ) to talk to the database
#----------------------------------------------------------
#database set up
#----------------------------------------------------------

from app.config import DATABASE_URL
# this will tell you app which db ->postgresql where ->localhost which user/password


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
# this will create a connection to the database

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) # craete a factory for databse sessions 
# autocommit=False -> dont commit the changes to the database until the session is closed
# autoflush=False -> dont flush the changes to the database until the session is closed
# bind=engine -> bind the session to the engine 
# this will create a session to the database
Base = declarative_base()
# used to create database tables using python classes
#----------------------------------------------------------
#authentication (JWT) set up
#----------------------------------------------------------
