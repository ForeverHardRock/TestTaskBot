import datetime
import pandas
import psycopg2
import os

from bot import bot
from dotenv import load_dotenv
from bs4 import BeautifulSoup

channel_id = os.getenv('CHANNEL_ID')


async def check_subscribe(user_id: int) -> bool:
    try:
        chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Error checking subscription: {e}")
        return False


async def db_connect():
    load_dotenv()
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('USER'),
        password=os.getenv('PASSWORD'),
        host=os.getenv('HOST'),
        port=os.getenv('PORT')
    )
    return conn


async def html_to_text(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')
    text = soup.get_text()
    return text


async def get_from_db(group, spec=None):
    conn = await db_connect()
    cur = conn.cursor()
    if spec:
        cur.execute(f"SELECT {group} FROM catalog_{group} WHERE {spec[0]} = %s", (spec[1],))
    else:
        cur.execute(f"SELECT {group} FROM catalog_{group}")
    cats = cur.fetchall()
    for i in range(len(cats)):
        cats[i] = cats[i][0]
    cur.close()
    conn.close()
    return cats


async def get_product(prod_name):
    conn = await db_connect()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM catalog_product WHERE product = %s", (prod_name,))
    product = cur.fetchone()
    format_product = {
        'prod_id': product[0],
        'prod_name': product[1],
        'prod_image': f"http://{os.getenv('HOST')}:{os.getenv('DJ_PORT')}/media/" + product[3],
        'prod_desc': await html_to_text(product[4]),
        'prod_price': product[5]
    }
    cur.close()
    conn.close()
    return format_product


async def save_to_cart(user_id, user_products):
    conn = await db_connect()
    cur = conn.cursor()
    cur.execute("SELECT items_in_cart FROM shopping_add_to_cart WHERE potential_buyer = %s", (str(user_id),))
    db_data = cur.fetchone()

    if db_data:
        db_data = eval(db_data[0])
        db_data.append(user_products)

        cur.execute("UPDATE shopping_add_to_cart SET items_in_cart = %s WHERE potential_buyer = %s",
                           (str(db_data), str(user_id)))
    else:
        cur.execute("INSERT INTO shopping_add_to_cart (potential_buyer, items_in_cart) VALUES (%s, %s)", (str(user_id), str([user_products]),))
    conn.commit()
    cur.close()
    conn.close()


async def get_user_cart(user_id):
    conn = await db_connect()
    cur = conn.cursor()
    cur.execute("SELECT items_in_cart FROM shopping_add_to_cart WHERE potential_buyer = %s", (str(user_id),))
    db_data = cur.fetchone()
    cur.close()
    conn.close()
    return db_data


async def delete_from_user_cart(user_id, pos):
    if type(pos) == str:
        pos = eval(pos)
    conn = await db_connect()
    cur = conn.cursor()
    cur.execute("SELECT items_in_cart FROM shopping_add_to_cart WHERE potential_buyer = %s", (str(user_id),))
    db_data = cur.fetchone()
    db_data = eval(db_data[0])
    db_data.remove(pos)
    if len(db_data) > 0:
        cur.execute("UPDATE shopping_add_to_cart SET items_in_cart = %s WHERE potential_buyer = %s",
                    (str(db_data), str(user_id)))
        conn.commit()
    else:
        await clean_cart(user_id)
    cur.close()
    conn.close()


async def clean_cart(user_id):
    conn = await db_connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM shopping_add_to_cart WHERE potential_buyer = %s", (str(user_id),))  # замените 1 на id нужной записи
    conn.commit()
    cur.close()
    conn.close()


async def order_to_db(positions, address, price, name, user_id):
    conn = await db_connect()
    cur = conn.cursor()
    order_time = datetime.datetime.now().replace(microsecond=0)

    cur.execute("INSERT INTO shopping_orders (order_products, order_summ, order_time, buyer_name, buyer_tg_id, buyer_address) VALUES (%s, %s, %s, %s, %s, %s) RETURNING order_id",
                (str(positions), int(price), order_time, name, user_id, address))

    order_id = cur.fetchone()[0]
    conn.commit()
    await client_update(user_id, name, order_id, address)
    await save_to_exel(order_id, positions, order_time, name, user_id, address)
    await clean_cart(user_id)

    cur.close()
    conn.close()


async def client_update(user_id, user_name, orders=None, addresses=None):
    conn = await db_connect()
    cur = conn.cursor()
    cur.execute("SELECT client_orders, client_addresses FROM clients_clients WHERE client_tg_id = %s",
                (str(user_id),))
    client_data = cur.fetchone()
    if orders and addresses:

        db_orders = eval(client_data[0])
        db_orders.append(orders)

        db_addresses = eval(client_data[1])
        if addresses not in db_addresses:
            db_addresses.append(addresses)

        cur.execute("UPDATE clients_clients SET client_orders = %s, client_addresses = %s WHERE client_tg_id = %s",
                    (str(db_orders), str(db_addresses), str(user_id),))

    else:
        if client_data is None:
            time_now = datetime.datetime.now().replace(microsecond=0)
            cur.execute("INSERT INTO clients_clients (client_name, client_tg_id, client_orders, client_addresses, client_time) VALUES (%s, %s, %s, %s, %s)",
                        (user_name, user_id, '[]', '[]', time_now))

    conn.commit()
    cur.close()
    conn.close()


async def save_to_exel(order_id, positions, order_time, buyer_name, user_id, address):
    ids, products, price, cols, price_cols, time, name, tg_id, adr = [], [], [], [], [], [], [], [], []
    for pos in positions:
        position = eval(pos)
        ids.append(order_id)
        products.append(position[0])
        price.append(position[1])
        cols.append(position[2])
        price_cols.append(position[3])
        time.append(order_time)
        name.append(buyer_name)
        tg_id.append(user_id)
        adr.append(address)

    data = {
        'Id заказа': ids,
        'Товары': products,
        'Цена': price,
        'Количество': cols,
        'Цена за количество': price_cols,
        'Время заказа': time,
        'Имя заказчика': name,
        'TG ID заказчика': tg_id,
        'Адрес доставки': adr,

    }

    df = pandas.DataFrame(data)
    print(df)
    existing_data = pandas.read_excel('orders.xlsx')
    combined_data = pandas.concat([existing_data, df], ignore_index=True)

    with pandas.ExcelWriter('orders.xlsx', engine='openpyxl') as writer:
        combined_data.to_excel(writer, index=False)


async def get_faq():
    conn = await db_connect()
    cur = conn.cursor()
    cur.execute("SELECT question, answer FROM faq_faq")
    q_a_s = cur.fetchall()
    faq = {}
    for q_a in q_a_s:
        faq.update({q_a[0]: await html_to_text(q_a[1])})
    cur.close()
    conn.close()
    return faq


async def check_mailing(time_now):
    conn = await db_connect()
    cur = conn.cursor()
    cur.execute("SELECT mail_text FROM clients_mailing WHERE mail_time > %s",(time_now,))
    mails = cur.fetchall()
    cur.close()
    conn.close()
    if len(mails) > 0:
        return mails


async def load_all_users():
    conn = await db_connect()
    cur = conn.cursor()
    cur.execute("SELECT client_tg_id FROM clients_clients")
    users_ids = cur.fetchall()
    cur.close()
    conn.close()
    if len(users_ids) > 0:
        return users_ids
