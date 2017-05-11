import sys
import agnostic
from milecastles import AnonymousContainer, Holder, Story, Card, signature, required, optional, debug
import boilerplate

templatePrefix = "{{% args {} %}}".format(signature)

def getTemplateId(story, node, templateName):
    return "{}_{}_{}".format(story.uid, node.uid, templateName)

def cacheTemplate(story, node, templateName):
    templateId = getTemplateId(story, node, templateName) # calculate the id
    templateResolver = boilerplate.Resolver(node)  # use node as resolver (referenced templates also attributes of node)
    templateJinja = getattr(node, templateName)  # get jinja source from attribute of node
    templateJinja = boilerplate.normaliseTemplate(templateJinja) # remove newlines, preceding or following whitespace, double spaces
    templateJinja = templatePrefix + templateJinja  # prefix the templateString with the standard argument signature
    templatePython = boilerplate.jinjaToPython(templateResolver, templateJinja) # create the python for the generatorFactory
    boilerplate.saveTemplatePython(templateId, templatePython) # place it as expected

def cardToDict(card):
    return dict(
        storyUid=card.storyUid,
        nodeUid=card.nodeUid,
        sack=card.sack
    )

def dictToCard(cardUid, cardDict):
    return Card(
        uid=cardUid,
        storyUid=cardDict["storyUid"],
        nodeUid=cardDict["nodeUid"],
        sack=cardDict["sack"]
    )

class Engine(AnonymousContainer):
    box = required
    card = None
    story = None
    node = None

    def __init__(self, *a, **k):
        super().__init__(*a, **k)

    def registerStory(self, story):
        return self._register(Story, story)
    
    def lookupStory(self, storyUid):
        return self._lookup(Story, storyUid)
                
    def handleCard(self, card):
        self.card = card
        self.story = self.lookupStory(card.storyUid)
        currentUid = card.nodeUid
        while self.node == None:
            currentNode = self.story.lookupNode(currentUid)
            redirectedUid = currentNode.activate(self)
            if redirectedUid != None and redirectedUid != currentUid:
                currentNode.deactivate(self)
                currentUid = redirectedUid
            else:
                self.setNode(currentNode)
        self.displayNode(self.node)
        self.node.deactivate(self)
        self.node = None
        self.story = None
        self.card = None
            
    def setNodeUid(self, nodeUid):
        node = self.story.lookupNode(nodeUid)
        return self.setNode(node)
    
    def setNode(self, node):
        self.node = node
        self.card.nodeUid = node.uid
        return self.node
            
    def getEngineContext(self):
        return dict(
            engine =    self, 
            story =     self.story,
            box =       self.box,
            node =      self.node,
            card =      self.card,
            sack =      Holder(**self.card.sack) # enables dot addressing of dictionary
        )
    
    def evaluateExpression(self, expression):
        result = eval(expression, self.getEngineContext())
        agnostic.collect()
        return result

    def displayNode(self, node):
        templateName = node.getRenderedTemplateName(self)
        templateId = getTemplateId(self.story, node, templateName)
        # TODO CH consider use of string hash of the template for lazy recompilation

        # CH suppress behaviour of dynamically compiling, runtime evaluating
        # generator = self.constructGenerator(node, templateString)

        # TODO CH add flag to suppress caching in development
        # CH instead load from module, (optionally lazy-create module)
        try:
            generatorFactory = boilerplate.loadTemplateGeneratorFactory(templateId)
        except ImportError as e:
            cacheTemplate(self.story, node, templateName)
            generatorFactory = boilerplate.loadTemplateGeneratorFactory(templateId)

        generator = generatorFactory(**self.getEngineContext())
        agnostic.collect()

        self.displayGeneratedText(generator)
        agnostic.collect()

        # TODO CH remove this block, which is not intended for final deployment
        if sys.implementation.name is not "micropython":
            maxLineLen = 25
            maxLineCount = 8

            def generator_to_string(generator):
                s = ""
                for chunk in generator:
                    s += chunk
                return s

            def check_layout(nodeUid, generator):
                s = generator_to_string(generator)
                lines = s.split("\n")
                if len(lines) > maxLineCount:
                    print()
                    print(s)
                    raise AssertionError("> {} lines in {}".format(maxLineCount, nodeUid))
                for line in lines:
                    if len(line) > maxLineLen:
                        print()
                        print(line)
                        raise AssertionError("> {} chars in {}".format(maxLineLen, nodeUid))

            check_layout(node.uid, generatorFactory(**self.getEngineContext()))

    '''Should render some text, in whatever form required by the Engine'''
    def displayGeneratedText(self, text):
        raise AssertionError("Not yet implemented")