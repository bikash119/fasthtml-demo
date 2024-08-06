from fasthtml.common import *
from hmac import compare_digest


#Initialize our database ( SQLite)
db = database('data/todos_app.db')
# The tables that we need in our database
todos,users = db.t.todos,db.t.users
if users not in db.t:
    # here we are defining the columns of our users table using dictionary
    users.create(dict(id=int,username=str,email=str,pwd=str),pk='id')
if todos not in db.t:
    # here we are defining the columns of our todos table using kwargs
    todos.create(id=int,title=str,done=bool,name=str,details=str,priority=int,pk='id')
# `dataclass` corresponding to our database tables are created here.
# Python Dataclass is similar to Java7 POJO with less boiler plate code
Todo,User = todos.dataclass(),users.dataclass()

# Anytime we want our users to get redirected to login screen, we can use this handy littl `login_redir` 
login_redir = RedirectResponse('/login',status_code=303)

# We want our system to intercept the request. A interceptor is usually used to either check if
# request has required information or to add more information before being handled by route handler.
# We are defining the behaviour of our interceptor
def before(req,sess):
    # Through this interceptor or *Beforeware* we want to intercept all request and check
    # if the user is authenticated. In order to check it, we try to get value of `auth` key 
    # from current session. If session has a value for key `auth`, it is stored in auth and
    # additionally stored in scope attribute of request object. 
    auth = req.scope['auth'] = sess.get('auth',None)
    # If the auth information is not available in session, we want the user to get
    # redirected to login screen.
    if not auth: return login_redir

    # `xtra` is part of MiniDataAPI spec. It adds filter to queries and DDL stmts.
    # If a user is authenticated, we want the system to show the todos which are owned / created by the 
    # the user. Hence, we are using the MiniDataAPI and passing the value of `auth` to name. This will internally 
    # create a sql query and add a where clause to the sql.
    todos.xtra(name=auth)

# Here we create our interceptor or *Beforeware*.We pass the function that defines the behaviour of our interceptor
# and list of paths which do not need the interceptor to be invoked.
# For any application, we do not want static files , favicon or request of css files to be intercepted. We can do
# but it will harm the performance of our system
bware = Beforeware(before,skip=[r'/favicon\.ico',r'/static/.*',r'.*\.css','/login'])

# We define a function to tell how the system will behave in case a page is not found.
def _not_found(req,exc): return Titled('oh ho!',Div('We could not find that page :('))

markdown_js = """
import { marked } from "https://cdn.jsdelivr.net/npm/marked/lib/marked.em.js"
import { proc_htmx } from "https://cds.jselivr.net/gh/answerdotai/fasthtml-js/fasthtml.js;
proc_htmx('.markdown',e=> e.innerHTML = marked.parse(e.textContent));
"""
# Now we create our app
# To create the app , we instantiate FastHTML by passing in 
# 1. the interceptor
# 2. Exception handler
# 3. 
app = FastHTML(before=bware # request interceptor
               ,exception_handlers={404:_not_found} # exception handler
               ,hdrs=(picolink) # picocss as stylesheet for our app
               )

# rt is shortcut for `app.route`, we will use to decorate our route handlers
# The name of the decorated function is used as HTTP verb for the handler
rt = app.route

# When the user lands up on login screen, we want to user to be able to type in their login credentials 
# and click on submit button to have them authenticated. 
# So we will create a form with two input fields and a submit button
@rt("/login")
def get():
    frm = Form(
         Input(id='username',placeholder='Name')
        ,Input(id='email',placeholder='email@domain.com')
        ,Input(id='passwd',type='password',placeholder='Password')
        ,Button('login')
        ,action='/login',method='post'
    )
    return Titled('Login',frm) # We are returning a HTML form titled Login

# The Login dataclass is auto instantiated for us. The attributes of the dataclass are populated from the values in the Form.
# The id of html tag is matched to attribute of dataclass
@dataclass
class Login: username: str; passwd: str; email: str

# This handler is invoked when POST request is made to the `/login` path
# The `login` argument is an instance of the `Login` class, which has been auto-instantiated from the form data.

@rt("/login")
def post(login:Login,sess):
    # if the login object doesn't have the name or password set, the user is redirected to login page.
    if not login.username or not login.passwd or not login.email: return login_redir
    try: 
        # Query the users table to find user by username
        u = users[login.username]
    except NotFoundError: 
        # if not found, create a user. 
        # TODO : invoke signup screen flow here.
        u = users.insert({'username':login.username,'email':login.email,'pwd':login.passwd})
    # Compare the passwords using a constant time string comparision
    if not compare_digest(u.pwd.encode('utf-8'),login.passwd.encode('utf-8')): return login_redir
    sess['auth'] = u.username
    return RedirectResponse('/',status_code=303)

# Instead or using the app.route, we can use app.<http_verb>. This will allow us to name our route handling functions
# different from http verb method.
@app.get("/logout")
def logout(sess):
    del sess['auth']
    return login_redir


# @patch decorator adds a method to an existing class.
# __ft__ is a special method that FastHTML uses to convert the object any object into `FT` object
# so that it can be converted (composed) into a FT tree and later rendered into HTML

# Here we are adding __ft__ method to Todo class which FastHTML will use and create FT tree of the Todo class
@patch
def __ft__(self:Todo):
    show = AX(self.title,f'/todos/{self.id}','current-todo')
    edit = AX('edit',    f'/todos/{self.id}','current-todo')
    dt = '✅ ' if self.done else ''
    cts = (dt, show, ' | ',edit,Hidden(id="id",value=self.id),Hidden(id="priority",value="0"))
    return Li(*cts,id=f'todo-{self.id}')

@rt("/")
def get(sess,auth):
    print(sess)
    title = f"{auth}'s Todo List"
    top = Grid(H1(title),Div(A('logout',href="/logout"),style='text-align: right'))
    # We do not want the user to land in a different page of adding or editing todos. So we will use hx_post to add
    # a new todo. The new todo is always added at the top of the list which we achieve by use `afterbegin`
    new_inp = Input(id="new-title",name="title", placeholder="New Todo") # A new input element is created here
    # Here we create a new form consisting of the input element new_inp and Button grouped together using Group FT
    add = Form(
            Group(new_inp,Button("Add"))
            ,hx_post="/", target_id="todo-list",hx_swap="afterbegin"
            )
    # Here we are rendering the list of Todos. 
    # 1. Since, as we have defined a interceptor to filter out Todos of the current user, so we need not add
    # any further filtering here.
    # 2. As we have patched our Todo class with __ft__ method, FastHTML will give us a FT tree for todos which will be 
    # rendered as HTML
    # 3. We are putting the Todos inside a Form so that we can use sortable in order to reorder/sort the Todos based
    # on user preference
    frm = Form(*todos(order_by='priority'),
               id='todo-list',cls='sortable',hx_post='/reorder',hx_trigger="end"
               )
    card = Card(Ul(frm),header=add,footer=Div(id='current-todo'))

    # What we are doing above is
    # 1. Creating a form to add the todos
    # 2. Creating a form to list down the todos
    # 3. Creating a Card which is capsule consisting of list of todos and add
    # 4. Finally creating container which is another capsule consisting of top grid and card
    return Title(title),Container(top,card)


@rt("/")
async def post(todo:Todo):
    # `hx_swap_oob= 'true'` tells htmx to perform an out-of-band swap, 
    #  What is out-of-band swap? : If the server responds a html element , then all the elements with the id same
    # as responded by server gets updated.
    # So , here we are explicitly returning the input element.
    # Since the id of this element is same as the input element we created in the get of `/`, the input element is updated.
    new_inp = Input(id="new-title",name="title",placeholder="New Todo",hx_swap_oob='true')
    return todos.insert(todo),new_inp
serve()
