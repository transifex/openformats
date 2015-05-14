def test_handler(Handler, source):
    print "## Source"
    print source
    print

    h = Handler()
    template, stringset = h.parse(source)

    print "## Stringset"
    for string in stringset:
        print "{}: {}".format(string.key, string.string)
    print

    print "## Template:"
    print template
    print

    compiled = h.compile(template, stringset)
    print "## Compiled"
    print compiled

    print "## Result"
    if source == compiled:
        print "Source is equal to compiled"
    else:
        print "Source is not equal to compiled"
