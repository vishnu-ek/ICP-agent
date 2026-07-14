from agent2.data2 import extractionMemory, icpAgentMemory
from agent2.pdfReader import PdfReader
from agent2.namedEntityExtractor import SpeakerExtractor
from agent2.icpvalidatorAgent import IcpValidatorAgent

class icpAgent:
    def __init__(self, client, model, goal, pdfPath, maxTokens=2048, maxIterations=3):
        self.client = client
        self.model = model
        self.pdfPath = pdfPath
        self.maxTokens = maxTokens
        self.goal = goal
        self.companies = set()
        self.companySpeakerMap = dict()

        self.pdfReader = PdfReader(pdfPath)
        self.speakerExtractor = SpeakerExtractor(self.client, self.model, maxTokens)
        self.icpvalidatorAgent = IcpValidatorAgent(self.client, self.model, maxTokens, maxIterations)
        self.extractionMemory = extractionMemory(goal=self.goal, pdfPath=self.pdfPath)
        self.icpAgentMemory = icpAgentMemory(goal=self.goal, pdfPath=self.pdfPath)

    def getCompanies(self, result):
        if result.error is None:
            for eachSpeakerEntry in result.speakers:
                com = eachSpeakerEntry.company
                nam = eachSpeakerEntry.name
                title = eachSpeakerEntry.title
                self.companies.add(com)
                if com not in self.companySpeakerMap:
                    self.companySpeakerMap[com] = list()
                self.companySpeakerMap[com].append((nam, title))

    def run(self):
        self.extractionMemory.totalPages = self.pdfReader.load()
        
        # currently extracting data sequentially, but can be parallised to reduce latency or even
        # pages can be grouped to limit reducing LLM calls
        for pageNo, eachPage in enumerate(self.pdfReader.pageTexts, start=1):
            print(pageNo, "##############")
            if not eachPage.strip():
                continue
                    
            result = self.speakerExtractor.extract(pageNo, eachPage)
            self.extractionMemory.chunkResults.append(result)
            self.getCompanies(result)
        print(f"Total unique companies: {len(self.companies)}")
        self.icpAgentMemory, dedicatedList = self.icpvalidatorAgent.evaluateAll(self.companySpeakerMap, self.icpAgentMemory)

        return self.icpAgentMemory, dedicatedList
