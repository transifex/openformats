def test_handler(Handler, source):
    print "## Source"
    print source
    print

    h = Handler()
    stringset = list(h.feed_content(source))

    print "## Stringset"
    for string in stringset:
        print "{}: {}".format(string.key, string.string)
    print

    print "## Template:"
    print h.template
    print

    compiled = h.compile(stringset)
    print "## Compiled"
    print compiled

    print "## Result"
    if source == compiled:
        print "Source is equal to compiled"
    else:
        print "Source is not equal to compiled"
