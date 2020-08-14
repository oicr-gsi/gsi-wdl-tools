import argparse
import WDL
import sys

def parse_inputs(args):
    print(type(args))
    print(args)
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-i", "--input-wdl-path", required = True, help = "source wdl path")
    parser.add_argument("-d", "--docker-image", required = False, help = "image name and tag")
    parser.add_argument("-j", "--pull-json", required = False, help = "path to json containing which variables to pull; don't specify --pull-all at the same time")
    parser.add_argument("-o", "--output-wdl-path", required = False, help = "output wdl path")
    parser.add_argument("-t", "--tab-size", required = False, help = "number of spaces in a tab")
    parser.add_argument("-p", "--pull-all", required = False, type=bool, help = "whether to pull all variables; don't specify --pull-json at the same time")
    parser.add_argument("-s", "--dockstore", required = False, type=bool, help = "whether to activate functions for dockstore")
    parser.add_argument("-w", "--import-metas", required = False, type=bool, help = "whether to pull parameter_metas from imported subworkflows")
    return parser.parse_args(args)

def main():
    parsed = parse_inputs(sys.argv[1:])
    print(type(parsed))
    print(parsed)

    #doc = WDL.load(input_wdl_path)  # loads the file as a WDL.Tree.Document object
    #print(doc.workflow.name)

if __name__ == "__main__":
    main()

