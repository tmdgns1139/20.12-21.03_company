####################################
# 1. package import
from flask import Flask, render_template, g, request, session, flash, redirect, url_for
import pandas as pd
import pymysql
import re
####################################


####################################
# 2. config
DEBUG = True
USERNAME = "admin"
PASSWORD = "888"
SECRET_KEY = "development key~~"
####################################


####################################
# 3. initialize
app = Flask(__name__)
app.config.from_object(__name__)

kDbName = "db_for_test"
kInitTableName = "coupang_product_table"
kTableNameForSelectedDatas = "selected_datas_table_revised"
kPathToCsv = \
    """
    ../../data/backup_dry_tissue_page8.csv
    """.strip()


def create_table(table_name):
    create_sql = \
        """
        CREATE TABLE {} (
        id INTEGER PRIMARY KEY NOT NULL AUTO_INCREMENT,
        code varchar(20),
        name varchar(200),
        brand_name varchar(20),
        hash_tag varchar(20),
        star varchar(20),
        star_count varchar(20),
        weight varchar(50),
        ml varchar(300),
        product_count varchar(50),
        price varchar(50),
        date varchar(30),
        flag varchar(20),
        ingredient_name varchar(200),
        view varchar(20),
        product_img_path varchar(200),
        product_detail_img_paths varchar(5000),
        product_url varchar(200)
        );
        """.format(table_name)
    with g.db.cursor() as cursor:
        cursor.execute(create_sql)
        g.db.commit()


def get_insert_sql(table_name):
    result = \
        """
        INSERT INTO {} (id, code, name, brand_name, hash_tag, star, star_count, weight, ml, product_count, price, date, flag, ingredient_name, view, product_img_path, product_detail_img_paths, product_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """.format(table_name)
    return result


def connect_db():
    return pymysql.connect(host='localhost',
                           db=kDbName,
                           user='root',
                           password='babylab123',
                           port=3306,
                           charset='utf8')


def init_db():
    with connect_db() as db:
        with db.cursor() as cursor:
            try:
                create_table(kInitTableName)
            except Exception as e:
                print(str(e))
            finally:
                cursor.execute("SELECT * FROM {}".format(kInitTableName))
                datas_from_db_table = cursor.fetchall()

                if not datas_from_db_table:
                    df = pd.read_csv(kPathToCsv, index_col=0)

                    for col in df.columns:
                        df[col] = df[col].apply(lambda x: "" if str(x) == 'nan' else str(x))
                        df[col] = df[col].apply(lambda x: x.replace(" , ", ",") if " , " in x else x)

                    df2numpy = df.to_numpy()
                    df2numpy2list = []
                    for data in df2numpy:
                        df2numpy2list.append(data.tolist())

                    insert_sql = get_insert_sql(kInitTableName)
                    cursor.executemany(insert_sql, df2numpy2list)
                    db.commit()
                cursor.close()
####################################


####################################
# 4. before_request & teardown_request
@app.before_request
def before_request():
    # HTTP ????????? ?????????????????? ??????
    g.db = connect_db()
    init_db()


@app.teardown_request
def teardown_request(exception):
    # HTTP ?????? ????????? ??????????????? ????????? ?????? ??????
    g.db.close()
####################################


####################################
# 5. views
@app.route("/")
def init_login():
    # ?????? ????????? ?????? ???????????? ???????????? ?????? ????????????.
    return render_template("login.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    # ????????? ?????? ????????? ???????????? ??????.
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = "Invalid username!"
        elif request.form['password'] != app.config['PASSWORD']:
            error = "Invalid password!"
        else:
            session['logged_in'] = True
            flash("login success")
            return redirect(url_for("show_selectable_elements"))
    return render_template("login.html", error=error)


@app.route("/logout", methods=['POST'])
def logout():
    # ???????????? ?????? ????????? ?????????.
    session.pop("logged_in", None)
    flash("logged out!")
    return redirect(url_for("login"))


@app.route("/main", methods=['GET', 'POST'])
def show_selectable_elements():
    # ????????? ??? ?????? ???????????? ?????????.
    datas = None
    with g.db.cursor() as cursor:
        cursor.execute("SELECT id, name, date FROM {};".format(kInitTableName))
        datas = cursor.fetchall()
        cursor.close()
    return render_template('show_selectable_elements.html', datas=datas)


@app.route("/main/revise", methods=['GET'])
def show_revising_element_from_main():
    # ?????? ?????? ???????????? ?????????. (???????????? main ?????? ?????? ??????)
    full_path = request.full_path
    before_parsing_id = re.compile("id=[0-9]+").search(full_path).group()
    after_parsing_id = before_parsing_id.split("=")[-1]

    select_sql = \
        """
        SELECT * FROM {}
        WHERE id = {};
        """.format(kInitTableName, after_parsing_id).strip()

    selected_data = None
    with g.db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(select_sql)
        selected_data = cursor.fetchone()

    return render_template("show_revising_data.html", datas=selected_data)


@app.route("/already_revised/revise", methods=['GET'])
def show_revising_element_from_already_revised():
    # ?????? ?????? ???????????? ?????????. (???????????? already_revised ?????? ?????? ??????)
    full_path = request.full_path
    before_parsing_id = re.compile("id=[0-9]+").search(full_path).group()
    after_parsing_id = before_parsing_id.split("=")[-1]

    select_sql = \
        """
        SELECT * FROM {}
        WHERE id = {};
        """.format(kTableNameForSelectedDatas, after_parsing_id).strip()

    selected_data = None
    with g.db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(select_sql)
        selected_data = cursor.fetchone()

    return render_template("show_revising_data.html", datas=selected_data)


@app.route("/main/revising", methods=['POST'])
@app.route("/already_revised/revising", methods=['POST'])
def revising():
    # ?????? ?????? ?????? ????????? ???????????? ??????
    revised_product_detail_paths = request.form.getlist("revised_product_detail_paths")
    revised_product_detail_path = ','.join(revised_product_detail_paths)

    revised_data_without_product_detail_paths = request.form.getlist("revised_element")
    revised_data = revised_data_without_product_detail_paths[:]
    for idx, element in enumerate(revised_data_without_product_detail_paths):
        if "/product_detail/" in element:
            revised_data[idx] = revised_product_detail_path
            break

    id = revised_data[0]
    insert_sql = get_insert_sql(kTableNameForSelectedDatas)

    try:
        create_table(kTableNameForSelectedDatas)
    finally:
        with g.db.cursor() as cursor:
            delete_sql = \
                """
                DELETE FROM {} WHERE id = {};
                """.format(kTableNameForSelectedDatas, id).strip()
            cursor.execute(delete_sql)
            cursor.execute(insert_sql, revised_data)

            g.db.commit()
            cursor.close()
        return redirect(url_for("already_revised"))


@app.route("/already_revised", methods=['GET', 'POST'])
def already_revised():
    # ??????, ????????? ??????????????? ????????? ?????? ????????????.
    try:
        create_table(kTableNameForSelectedDatas)
    finally:
        showing_datas = None
        with g.db.cursor(pymysql.cursors.DictCursor) as cursor:
            select_sql = \
                """
                SELECT id, name, price, date, ingredient_name FROM {}
                """.format(kTableNameForSelectedDatas).strip()
            cursor.execute(select_sql)
            showing_datas = cursor.fetchall()
        return render_template("show_revised_data.html", datas=showing_datas)


@app.route("/main/just_view", methods=['GET'])
def just_view_for_init():
    # ???????????? ????????? ???????????????,
    full_path = request.full_path
    print(full_path)
    id = re.compile("id=[0-9]+").search(full_path).group().split("=")[-1]

    selected_sql = \
        """
        SELECT * FROM {}
        WHERE id = {}
        """.format(kInitTableName, id)

    selected_data = None
    with g.db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(selected_sql)
        selected_data = cursor.fetchone()
    return render_template('just_view_for_selected_data.html', datas=selected_data)


@app.route("/already_revised/just_view", methods=['GET'])
def just_view_for_selected():
    full_path = request.full_path
    id = re.compile("id=[0-9]+").search(full_path).group().split("=")[-1]
    select_sql = \
        """
        SELECT * FROM {}
        WHERE id = {}
        """.format(kTableNameForSelectedDatas, id)

    selected_data = None
    with g.db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(select_sql)
        selected_data = cursor.fetchone()
    return render_template('just_view_for_selected_data.html', datas=selected_data)


@app.route("/delete_data", methods=['GET', 'POST'])
def delete_data():
    delete_data_id = request.form.get("deleted_data_id")

    delete_sql = \
        """
        DELETE FROM {}
        WHERE id = {}
        """.format(kTableNameForSelectedDatas, delete_data_id)

    with g.db.cursor() as cursor:
        cursor.execute(delete_sql)
        g.db.commit()

    return redirect(url_for("already_revised"))
####################################


####################################
# 6. template_filter
@app.template_filter("is_name")
def is_name(any_element):
    try:
        int(any_element)
        return False
    except:
        try:
            int(any_element[:4])
            return False
        except:
            return True


@app.template_filter("to_string")
def to_string(any_element):
    return str(any_element)


@app.template_filter("split_by_comma")
def split_by_comma(img_paths):
    return img_paths.split(",")


@app.template_filter("is_empty")
def is_empty(a_list):
    return False if a_list else True
####################################


if __name__ == '__main__':
    app.run()

