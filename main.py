from fasthtml.common import *
from hmac import compare_digest


#Initialize our database ( SQLite)
db = database('data/todos_app.db')
# The tables that we need in our database
todos,users = db.t.todos,db.t.users
if users not in db.t:
    # here we are defining the columns of our users table using dictionary
    users.create(dict(id=int,name=str,pwd=str),pk='id')
if todos not in db.t:
    # here we are defining the columns of our todos table using kwargs
    todos.create(id=int,title=str,name=str,details=str,priority=int,pk='id')
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
         Input(id='name',placeholder='Name')
        ,Input(id='password',type='password',placeholder='Password')
        ,Button('login')
        ,action='/login',method='post'
    )
    return Titled('Login',frm) # We are returning a HTML form titled Login

serve()

