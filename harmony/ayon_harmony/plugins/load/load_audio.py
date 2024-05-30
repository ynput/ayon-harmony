from ayon_core.pipeline import (
    load,
    get_representation_path,
)
import ayon_core.hosts.harmony.api as harmony

sig = harmony.signature()
func = """
function getUniqueColumnName( column_prefix )
{
    var suffix = 0;
    // finds if unique name for a column
    var column_name = column_prefix;
    while(suffix < 2000)
    {
        if(!column.type(column_name))
        break;

        suffix = suffix + 1;
        column_name = column_prefix + "_" + suffix;
    }
    return column_name;
}

function %s(args)
{
    var uniqueColumnName = getUniqueColumnName(args[0]);
    column.add(uniqueColumnName , "SOUND");
    column.importSound(uniqueColumnName, 1, args[1]);
}
%s
""" % (sig, sig)


class ImportAudioLoader(load.LoaderPlugin):
    """Import audio."""

    product_types = {"shot", "audio"}
    representations = {"wav"}
    label = "Import Audio"

    def load(self, context, name=None, namespace=None, data=None):
        wav_file = get_representation_path(context["representation"])
        harmony.send(
            {"function": func, "args": [context["product"]["name"], wav_file]}
        )

        product_name = context["product"]["name"]

        return harmony.containerise(
            product_name,
            namespace,
            product_name,
            context,
            self.__class__.__name__
        )

    def update(self, container, context):
        pass

    def remove(self, container):
        pass
