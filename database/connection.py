import pymysql
from flask_mysqldb import MySQL
from config import Config


mysql = MySQL()


def init_db(app):
    """
    Initialize Flask-MySQLdb using the application configuration.
    """

    app.config["MYSQL_HOST"] = Config.MYSQL_HOST
    app.config["MYSQL_USER"] = Config.MYSQL_USER
    app.config["MYSQL_PASSWORD"] = Config.MYSQL_PASSWORD
    app.config["MYSQL_DB"] = Config.MYSQL_DB
    app.config["MYSQL_PORT"] = Config.MYSQL_PORT
    app.config["MYSQL_CURSORCLASS"] = Config.MYSQL_CURSORCLASS

    mysql.init_app(app)

    return mysql


def get_db_connection():
    """
    Optional direct PyMySQL connection.
    Use this only when needed outside the Flask mysql object.
    """

    connection = pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        port=Config.MYSQL_PORT,
        cursorclass=pymysql.cursors.DictCursor
    )

    return connection