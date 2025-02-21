# Harmony Integration

## Setup

The easiest way to setup for using Toon Boom Harmony is to use the built-in launch:

```
python -c "import ayon_harmony.api as harmony;harmony.launch("path/to/harmony/executable")"
```

Communication with Harmony happens with a server/client relationship where the server is in the Python process and the client is in the Harmony process. Messages between Python and Harmony are required to be dictionaries, which are serialized to strings:
```
+------------+
|            |
|   Python   |
|   Process  |
|            |
| +--------+ |
| |        | |
| |  Main  | |
| | Thread | |
| |        | |
| +----^---+ |
|     ||     |
|     ||     |
| +---v----+ |     +---------+
| |        | |     |         |
| | Server +-------> Harmony |
| | Thread <-------+ Process |
| |        | |     |         |
| +--------+ |     +---------+
+------------+
```

Server/client now uses stricter protocol to handle communication. This is necessary because of precise control over data passed between server/client. Each message is prepended with 6 bytes:
```
| A | H | 0x00 | 0x00 | 0x00 | 0x00 | ...

```
First two bytes are *magic* bytes stands for **A**yon **H**armony. Next four bytes hold length of the message `...` encoded as 32bit unsigned integer. This way we know how many bytes to read from the socket and if we need more or we need to parse multiple messages.


## Usage

The integration creates an `AYON` menu entry where all related tools are located.

**NOTE: Menu creation can be temperamental. The best way is to launch Harmony and do nothing else until Harmony is fully launched.**

### Work files

Because Harmony projects are directories, this integration uses `.zip` as work file extension. Internally the project directories are stored under `[User]/.ayon/harmony`. Whenever the user saves the `.xstage` file, the integration zips up the project directory and moves it to the AYON project path. Zipping and moving happens in the background.

### Show Workfiles on launch

You can show the Workfiles app when Harmony launches by setting environment variable `AYON_HARMONY_WORKFILES_ON_LAUNCH=1`.

## Developing

### Low level messaging
To send from Python to Harmony you can use the exposed method:
```python
import ayon_harmony.api as harmony
from uuid import uuid4


func = """function %s_hello(person)
{
  return ("Hello " + person + "!");
}
%s_hello
""" % (uuid4(), uuid4())
print(harmony.send({"function": func, "args": ["Python"]})["result"])
```
**NOTE:** Its important to declare the function at the end of the function string. You can have multiple functions within your function string, but the function declared at the end is what gets executed.

To send a function with multiple arguments its best to declare the arguments within the function:
```python
import ayon_harmony.api as harmony
from uuid import uuid4

signature = str(uuid4()).replace("-", "_")
func = """function %s_hello(args)
{
  var greeting = args[0];
  var person = args[1];
  return (greeting + " " + person + "!");
}
%s_hello
""" % (signature, signature)
print(harmony.send({"function": func, "args": ["Hello", "Python"]})["result"])
```

### Caution

When naming your functions be aware that they are executed in global scope. They can potentially clash with Harmony own function and object names.
For example `func` is already existing Harmony object. When you call your function `func` it will overwrite in global scope the one from Harmony, causing
erratic behavior of Harmony. AYON is prefixing those function names with [UUID4](https://docs.python.org/3/library/uuid.html) making chance of such clash minimal.
See above examples how that works. This will result in function named `38dfcef0_a6d7_4064_8069_51fe99ab276e_hello()`.
You can find list of Harmony object and function in Harmony documentation.

### Higher level (recommended)

Instead of sending functions directly to Harmony, it is more efficient and safe to just add your code to `js/AyonHarmony.js` or utilize `{"script": "..."}` method.

#### Extending AyonHarmony.js

Add your function to `AyonHarmony.js`. For example:

```javascript
AyonHarmony.myAwesomeFunction = function() {
  someCoolStuff();
};
```
Then you can call that javascript code from your Python like:

```Python
import ayon_harmony.api as harmony

harmony.send({"function": "AyonHarmony.myAwesomeFunction"});

```

#### Using Script method

You can also pass whole scripts into harmony and call their functions later as needed.

For example, you have bunch of javascript files:

```javascript
/* Master.js */

var Master = {
  Foo = {};
  Boo = {};
};

/* FileA.js */
var Foo = function() {};

Foo.prototype.A = function() {
  someAStuff();
}

// This will construct object Foo and add it to Master namespace.
Master.Foo = new Foo();

/* FileB.js */
var Boo = function() {};

Boo.prototype.B = function() {
  someBStuff();
}

// This will construct object Boo and add it to Master namespace.
Master.Boo = new Boo();
```

Now in python, just read all those files and send them to Harmony.

```python
from pathlib import Path
import ayon_harmony.api as harmony

path_to_js = Path('/path/to/my/js')
script_to_send = ""

for file in path_to_js.iterdir():
  if file.suffix == ".js":
    script_to_send += file.read_text()

harmony.send({"script": script_to_send})

# and use your code in Harmony
harmony.send({"function": "Master.Boo.B"})

```

### Scene Save
Instead of sending a request to Harmony with `scene.saveAll` please use:
```python
import ayon_harmony.api as harmony
harmony.save_scene()
```

<details>
  <summary>Click to expand for details on scene save.</summary>

  Because AYON tools do not deal well with folders for a single entity like a Harmony scene, this integration has implemented to use zip files to encapsulate the Harmony scene folders. Saving scene in Harmony via menu or CTRL+S will not result in producing zip file, only saving it from Workfiles will. This is because
  zipping process can take some time in which we cannot block user from saving again. If xstage file is changed during zipping process it will produce corrupted zip
  archive.
</details>


## Resources
- https://github.com/diegogarciahuerta/tk-harmony
- https://github.com/cfourney/OpenHarmony
- [Toon Boom Discord](https://discord.gg/syAjy4H)
- [Toon Boom TD](https://discord.gg/yAjyQtZ)
