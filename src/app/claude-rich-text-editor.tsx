// src/components/MunEditor.jsx
import React, { useState, useEffect, useRef } from 'react';
import { Editor } from '@tinymce/tinymce-react';
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Save, Clock, BookOpen, FileText, Settings, Brain } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import getTinyMCEConfig from '../utils/tinymceConfig';
import axios from 'axios';

// API URL constant - replace with your actual API URL in production
const API_URL = 'http://localhost:5000/api';

// Bibliography generation helper
const generateCitation = (type, data) => {
  if (type === 'book') {
    return `${data.author}. (${data.year}). ${data.title}. ${data.publisher}.`;
  } else if (type === 'article') {
    return `${data.author}. (${data.year}). ${data.title}. ${data.journal}, ${data.volume}(${data.issue}), ${data.pages}.`;
  } else if (type === 'website') {
    return `${data.author}. (${data.year}). ${data.title}. Retrieved from ${data.url}`;
  }
  return '';
};

const MunEditor = ({ documentId, initialTitle }) => {
  const editorRef = useRef(null);
  const [content, setContent] = useState('');
  const [documentTitle, setDocumentTitle] = useState(initialTitle || 'Untitled Document');
  const [currentVersion, setCurrentVersion] = useState(1);
  const [versionHistory, setVersionHistory] = useState([]);
  const [citations, setCitations] = useState([]);
  const [citationData, setCitationData] = useState({
    type: 'book',
    author: '',
    year: '',
    title: '',
    publisher: '',
    journal: '',
    volume: '',
    issue: '',
    pages: '',
    url: ''
  });
  const [headerFooterSettings, setHeaderFooterSettings] = useState({
    header: 'MODEL UNITED NATIONS',
    footer: 'Page {page} of {pages}'
  });
  const [showCitationDialog, setShowCitationDialog] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState('');
  const [isProcessingAI, setIsProcessingAI] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(true);
  const [editorReady, setEditorReady] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  
  // Common MUN phrases for quick insertion
  const munPhrases = {
    preamble: [
      "Affirming", "Alarmed by", "Aware of", "Bearing in mind", "Believing", 
      "Confident", "Contemplating", "Convinced", "Declaring", "Deeply concerned", 
      "Deeply conscious", "Deeply disturbed", "Desiring", "Emphasizing", "Expecting", 
      "Fulfilling", "Fully aware", "Guided by", "Having adopted", "Having considered",
      "Noting with regret", "Noting with satisfaction", "Reaffirming", "Realizing", "Recalling"
    ],
    operative: [
      "Accepts", "Affirms", "Approves", "Authorizes", "Calls upon", "Condemns", 
      "Confirms", "Congratulates", "Considers", "Declares accordingly", "Deplores", 
      "Designates", "Draws attention", "Emphasizes", "Encourages", "Endorses", 
      "Expresses its appreciation", "Further invites", "Further proclaims", "Further requests",
      "Notes", "Proclaims", "Reaffirms", "Recommends", "Reminds", "Requests", "Resolves"
    ]
  };

ISOString(), title: 'Initial draft' }
    ]);
  }, []);

  const handleEditorChange = (content) => {
    setContent(content);
    localStorage.setItem('munEditorContent', content);
  };

  const saveVersion = () => {
    const newVersion = {
      id: currentVersion + 1,
      timestamp: new Date().toISOString(),
      title: `Version ${currentVersion + 1}`,
      content: content
    };
    
    setVersionHistory([...versionHistory, newVersion]);
    setCurrentVersion(currentVersion + 1);
    
    // In a real app, you would save to backend
    // axios.post('/api/save-version', newVersion);

    // For demo, we'll save to localStorage
    localStorage.setItem('munEditorVersions', JSON.stringify([...versionHistory, newVersion]));
  };

  const loadVersion = (version) => {
    // In a real app, you would fetch from backend
    const versions = JSON.parse(localStorage.getItem('munEditorVersions') || '[]');
    const versionToLoad = versions.find(v => v.id === version);
    
    if (versionToLoad && versionToLoad.content) {
      setContent(versionToLoad.content);
      setCurrentVersion(version);
    }
  };

  const addCitation = async () => {
    try {
      const citation = generateCitation(citationData.type, citationData);
      const newCitations = [...citations, citation];
      setCitations(newCitations);
      
      // In a real app, save to backend
      // await axios.post(`${API_URL}/documents/${documentId}/citations`, citationData);
      
      // Insert citation reference in editor
      if (editorRef.current) {
        const citationIndex = newCitations.length;
        editorRef.current.insertContent(`<sup>[${citationIndex}]</sup>`);
      }
      
      // Clear form and close dialog
      setCitationData({
        type: 'book',
        author: '',
        year: '',
        title: '',
        publisher: '',
        journal: '',
        volume: '',
        issue: '',
        pages: '',
        url: ''
      });
      setShowCitationDialog(false);
      
      setSuccessMessage('Citation added successfully');
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (error) {
      console.error('Error adding citation:', error);
      setErrorMessage('Failed to add citation');
      setTimeout(() => setErrorMessage(''), 3000);
    }
  };

  const generateBibliography = () => {
    if (editorRef.current) {
      if (citations.length === 0) {
        setErrorMessage('No citations to generate bibliography');
        setTimeout(() => setErrorMessage(''), 3000);
        return;
      }
      
      let bibliography = '<h2>Bibliography</h2><ol>';
      citations.forEach(citation => {
        bibliography += `<li>${citation}</li>`;
      });
      bibliography += '</ol>';
      
      editorRef.current.insertContent(bibliography);
      
      setSuccessMessage('Bibliography generated successfully');
      setTimeout(() => setSuccessMessage(''), 3000);
    }
  };

  const updateHeaderFooter = () => {
    // In a real implementation, this would update the actual document header/footer
    // For TinyMCE, this requires configuring the editor with the updated settings
    if (editorRef.current) {
      // Update editor config
      const newConfig = getTinyMCEConfig(
        headerFooterSettings.header,
        headerFooterSettings.footer
      );
};

export { MunEditor };
      
      // For a real implementation, you would need to reinitialize the editor
      // or use a TinyMCE API method to update these settings
      
      setSuccessMessage('Header and footer settings updated');
      setTimeout(() => setSuccessMessage(''), 3000);
    }
  };

  const getAISuggestions = async () => {
    setIsProcessingAI(true);
    setAiSuggestion('');
    
    try {
      // In a real app, you would call your AI service
      // const response = await axios.post(`${API_URL}/ai-suggestions`, { 
      //   content,
      //   document_id: documentId
      // });
      // setAiSuggestion(response.data.suggestion);
      
      // Mock AI response for demo
      setTimeout(() => {
        // Generate different suggestions based on content keywords
        const contentLower = content.toLowerCase();
        let suggestion = '';
        
        if (contentLower.includes('climate') || contentLower.includes('environment')) {
          suggestion = "Consider strengthening your position statement on climate action by referencing the latest IPCC report. Also, your economic impact analysis could benefit from more specific data points.";
        } else if (contentLower.includes('security') || contentLower.includes('peacekeeping')) {
          suggestion = "Your security arguments would be more compelling with recent examples from conflict zones. Consider adding statistics about the human cost of the conflict to strengthen your humanitarian appeal.";
        } else if (contentLower.includes('health') || contentLower.includes('pandemic')) {
          suggestion = "Your health proposals could be strengthened by citing WHO guidelines. Consider adding more details about funding mechanisms and implementation timelines for your healthcare initiatives.";
        } else if (contentLower.includes('economic') || contentLower.includes('development')) {
          suggestion = "Your economic analysis would benefit from more recent GDP figures. Consider addressing potential counterarguments about debt sustainability in developing nations.";
        } else {
          suggestion = "Consider using more formal diplomatic language in your clauses. Your resolution would be strengthened by adding more specific action items and implementation details.";
        }
        
        setAiSuggestion(suggestion);
        setIsProcessingAI(false);
      }, 2000);
    } catch (error) {
      console.error('Error getting AI suggestions:', error);
      setErrorMessage('Failed to get AI suggestions');
      setTimeout(() => setErrorMessage(''), 3000);
      setIsProcessingAI(false);
    }
  };
  
  const insertMunPhrase = (type, phrase) => {
    if (!editorRef.current) return;
    
    if (type === 'preamble') {
      editorRef.current.insertContent(`<p class="preamble-clause"><em>${phrase}</em> </p>`);
    } else {
      editorRef.current.insertContent(`<p class="operative-clause">${phrase} </p>`);
    }
  };

  return (
    <div className="flex flex-col h-full max-w-6xl mx-auto p-4">
      {/* Document header with title and version controls */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <Input 
            value={documentTitle} 
            onChange={(e) => setDocumentTitle(e.target.value)}
            className="text-lg font-bold w-64"
          />
          <div className="flex items-center gap-1">
            <Badge variant="outline" className="text-xs">v{currentVersion}</Badge>
            {lastSaved && (
              <span className="text-xs text-gray-500 flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Last saved: {lastSaved.toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center space-x-2 mr-2">
            <Switch 
              id="autosave" 
              checked={autoSaveEnabled}
              onCheckedChange={setAutoSaveEnabled}
            />
            <Label htmlFor="autosave" className="text-xs">Autosave</Label>
          </div>
          <Select onValueChange={(value) => loadVersion(parseInt(value))}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Version history" />
            </SelectTrigger>
            <SelectContent>
              {versionHistory.map((version) => (
                <SelectItem key={version.id} value={version.id.toString()}>
                  {version.title} ({new Date(version.timestamp).toLocaleString()})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={() => saveVersion(false)} disabled={isSaving}>
            {isSaving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
            Save
          </Button>
        </div>
      </div>

      {/* Status messages */}
      {successMessage && (
        <Alert className="mb-4 bg-green-50 border-green-200">
          <AlertTitle className="text-green-800">Success</AlertTitle>
          <AlertDescription className="text-green-700">{successMessage}</AlertDescription>
        </Alert>
      )}
      
      {errorMessage && (
        <Alert className="mb-4 bg-red-50 border-red-200">
          <AlertTitle className="text-red-800">Error</AlertTitle>
          <AlertDescription className="text-red-700">{errorMessage}</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="editor" className="flex flex-col flex-grow">
        <TabsList>
          <TabsTrigger value="editor" className="flex items-center gap-1">
            <FileText className="h-4 w-4" />
            Editor
          </TabsTrigger>
          <TabsTrigger value="settings" className="flex items-center gap-1">
            <Settings className="h-4 w-4" />
            Document Settings
          </TabsTrigger>
          <TabsTrigger value="ai" className="flex items-center gap-1">
            <Brain className="h-4 w-4" />
            AI Assistant
          </TabsTrigger>
          <TabsTrigger value="bibliography" className="flex items-center gap-1">
            <BookOpen className="h-4 w-4" />
            Bibliography
          </TabsTrigger>
        </TabsList>
        
        {/* Editor Tab */}
        <TabsContent value="editor" className="flex-grow">
          <Card className="flex flex-col h-full">
            <CardContent className="pt-4 flex-grow">
              {!editorReady ? (
                <div className="h-full flex items-center justify-center">
                  <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                </div>
              ) : (
                <Editor
                  onInit={(evt, editor) => editorRef.current = editor}
                  initialValue={content}
                  value={content}
                  onEditorChange={handleEditorChange}
                  init={getTinyMCEConfig(headerFooterSettings.header, headerFooterSettings.footer)}
                />
              )}
            </CardContent>
            <CardFooter className="flex justify-between">
              <div className="flex flex-wrap gap-2">
                <Dialog open={showCitationDialog} onOpenChange={setShowCitationDialog}>
                  <DialogTrigger asChild>
                    <Button variant="outline" size="sm">Add Citation</Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Add Citation</DialogTitle>
                      <DialogDescription>
                        Enter the details for your citation.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                      <div className="space-y-2">
                        <Label>Citation Type</Label>
                        <Select 
                          value={citationData.type} 
                          onValueChange={(value) => setCitationData({...citationData, type: value})}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select type" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="book">Book</SelectItem>
                            <SelectItem value="article">Article</SelectItem>
                            <SelectItem value="website">Website</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      
                      {citationData.type === 'book' && (
                        <div className="space-y-2">
                          <Label>Publisher</Label>
                          <Input 
                            value={citationData.publisher}
                            onChange={(e) => setCitationData({...citationData, publisher: e.target.value})}
                          />
                        </div>
                      )}
                      
                      {citationData.type === 'article' && (
                        <>
                          <div className="space-y-2">
                            <Label>Journal</Label>
                            <Input 
                              value={citationData.journal}
                              onChange={(e) => setCitationData({...citationData, journal: e.target.value})}
                            />
                          </div>
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <Label>Volume</Label>
                              <Input 
                                value={citationData.volume}
                                onChange={(e) => setCitationData({...citationData, volume: e.target.value})}
                              />
                            </div>
                            <div className="space-y-2">
                              <Label>Issue</Label>
                              <Input 
                                value={citationData.issue}
                                onChange={(e) => setCitationData({...citationData, issue: e.target.value})}
                              />
                            </div>
                          </div>
                          <div className="space-y-2">
                            <Label>Pages</Label>
                            <Input 
                              value={citationData.pages}
                              onChange={(e) => setCitationData({...citationData, pages: e.target.value})}
                            />
                          </div>
                        </>
                      )}
                      
                      {citationData.type === 'website' && (
                        <div className="space-y-2">
                          <Label>URL</Label>
                          <Input 
                            value={citationData.url}
                            onChange={(e) => setCitationData({...citationData, url: e.target.value})}
                          />
                        </div>
                      )}
                    </div>
                    <DialogFooter>
                      <Button type="submit" onClick={addCitation}>Add Citation</Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
                
                <Select onValueChange={(value) => {
                  const [type, phrase] = value.split('|');
                  insertMunPhrase(type, phrase);
                }}>
                  <SelectTrigger className="w-48">
                    <SelectValue placeholder="MUN Phrases" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="header|Preamble Clauses" disabled>Preamble Clauses</SelectItem>
                    {munPhrases.preamble.map((phrase) => (
                      <SelectItem key={`preamble|${phrase}`} value={`preamble|${phrase}`}>
                        {phrase}
                      </SelectItem>
                    ))}
                    <SelectItem value="header|Operative Clauses" disabled>Operative Clauses</SelectItem>
                    {munPhrases.operative.map((phrase) => (
                      <SelectItem key={`operative|${phrase}`} value={`operative|${phrase}`}>
                        {phrase}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardFooter>
          </Card>
        </TabsContent>
        
        {/* Document Settings Tab */}
        <TabsContent value="settings">
          <Card>
            <CardHeader>
              <CardTitle>Document Settings</CardTitle>
              <CardDescription>
                Configure header, footer, and other document settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Header Text</Label>
                <Input 
                  value={headerFooterSettings.header}
                  onChange={(e) => setHeaderFooterSettings({...headerFooterSettings, header: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>Footer Text</Label>
                <Input 
                  value={headerFooterSettings.footer}
                  onChange={(e) => setHeaderFooterSettings({...headerFooterSettings, footer: e.target.value})}
                  placeholder="Use {page} and {pages} as placeholders"
                />
              </div>
              <Button onClick={updateHeaderFooter}>Update Header/Footer</Button>
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* AI Assistant Tab */}
        <TabsContent value="ai">
          <Card>
            <CardHeader>
              <CardTitle>AI Writing Assistant</CardTitle>
              <CardDescription>
                Get suggestions to improve your MUN document
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button 
                onClick={getAISuggestions} 
                disabled={isProcessingAI}
                className="w-full"
              >
                {isProcessingAI ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Analyzing document...
                  </>
                ) : (
                  <>
                    <Brain className="h-4 w-4 mr-2" />
                    Analyze Document for Suggestions
                  </>
                )}
              </Button>
              
              {aiSuggestion && (
                <div className="mt-4 p-4 bg-blue-50 rounded-md border border-blue-200">
                  <h3 className="text-sm font-medium mb-2">AI Suggestions:</h3>
                  <p>{aiSuggestion}</p>
                  <div className="mt-4 flex justify-end">
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => {
                        if (editorRef.current) {
                          editorRef.current.selection.setContent('<span class="ai-highlight" style="background-color: #e6f7ff; padding: 0 2px;">' + editorRef.current.selection.getContent() + '</span>');
                        }
                      }}
                    >
                      Highlight Selection as Modified
                    </Button>
                  </div>
                </div>
              )}
              
              <div className="mt-6 space-y-4">
                <h3 className="text-sm font-medium">Common MUN Phrases</h3>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    "The delegate of [country] wishes to...",
                    "This resolution addresses the issue of...",
                    "My delegation strongly believes that...",
                    "Point of parliamentary inquiry...",
                    "The chair recognizes...",
                    "Motion to move to voting procedures..."
                  ].map((phrase, i) => (
                    <Button 
                      key={i} 
                      variant="outline" 
                      className="justify-start h-auto py-2"
                      onClick={() => editorRef.current?.insertContent(phrase)}
                    >
                      {phrase}
                    </Button>
                  ))}
                </div>
              </div>
              
              <div className="mt-6 space-y-4">
                <h3 className="text-sm font-medium">MUN Document Templates</h3>
                <div className="grid grid-cols-1 gap-2">
                  {[
                    { name: "Resolution Template", content: `<div class="resolution-title">DRAFT RESOLUTION</div>
<div>Committee: [Committee Name]</div>
<div>Topic: [Topic]</div>
<div>Sponsors: [Sponsoring Countries]</div>

<h2>The [Committee Name],</h2>

<p class="preamble-clause"><em>Recalling</em> previous resolutions regarding this matter,</p>
<p class="preamble-clause"><em>Deeply concerned</em> about the ongoing situation,</p>
<p class="preamble-clause"><em>Recognizing</em> the need for international cooperation,</p>

<p class="operative-clause">Calls upon all member states to address this issue;</p>
<p class="operative-clause">Requests the Secretary-General to provide resources;</p>
<p class="operative-clause">Decides to remain actively seized of the matter.</p>` },
                    { name: "Position Paper Template", content: `<div class="country-header">[COUNTRY NAME]</div>
<div>Committee: [Committee Name]</div>
<div>Topic: [Topic]</div>

<h2>I. Background of the Topic</h2>
<p>[Insert background information here]</p>

<h2>II. [Country Name]'s Position</h2>
<p>[Insert country's position here]</p>

<h2>III. Proposed Solutions</h2>
<p>[Insert proposed solutions here]</p>` },
                    { name: "Working Paper Template", content: `<div class="resolution-title">WORKING PAPER</div>
<div>Committee: [Committee Name]</div>
<div>Topic: [Topic]</div>
<div>Submitters: [Submitting Countries]</div>

<h2>1. Introduction</h2>
<p>[Insert introduction here]</p>

<h2>2. Proposed Solutions</h2>
<ul>
  <li>[Solution 1]</li>
  <li>[Solution 2]</li>
  <li>[Solution 3]</li>
</ul>

<h2>3. Implementation</h2>
<p>[Insert implementation details here]</p>` }
                  ].map((template, i) => (
                    <Button 
                      key={i} 
                      variant="outline" 
                      className="justify-start h-auto py-2"
                      onClick={() => {
                        if (editorRef.current && window.confirm('This will replace your current content. Are you sure?')) {
                          editorRef.current.setContent(template.content);
                        }
                      }}
                    >
                      {template.name}
                    </Button>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* Bibliography Tab */}
        <TabsContent value="bibliography">
          <Card>
            <CardHeader>
              <CardTitle>Bibliography Management</CardTitle>
              <CardDescription>
                Manage citations and generate bibliography
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between mb-4">
                <h3 className="text-sm font-medium">Current Citations</h3>
                <div className="space-x-2">
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={generateBibliography}
                    disabled={citations.length === 0}
                  >
                    <BookOpen className="h-4 w-4 mr-2" />
                    Generate Bibliography
                  </Button>
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={() => setShowCitationDialog(true)}
                  >
                    Add Citation
                  </Button>
                </div>
              </div>
              
              {citations.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <BookOpen className="h-16 w-16 mx-auto mb-4 opacity-20" />
                  <p>No citations added yet</p>
                </div>
              ) : (
                <div className="border rounded-md overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">#</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Citation</th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {citations.map((citation, index) => (
                        <tr key={index}>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                            [{index + 1}]
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-500">
                            {citation}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                const newCitations = [...citations];
                                newCitations.splice(index, 1);
                                setCitations(newCitations);
                              }}
                            >
                              Remove
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
                      
                      <div className="space-y-2">
                        <Label>Author</Label>
                        <Input 
                          value={citationData.author}
                          onChange={(e) => setCitationData({...citationData, author: e.target.value})}
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label>Year</Label>
                        <Input 
                          value={citationData.year}
                          onChange={(e) => setCitationData({...citationData, year: e.target.value})}
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label>Title</Label>
                        <Input 
                          value={citationData.title}
                          onChange={(e) => setCitationData({...citationData, title: e.target.value})}
                        />
                      </div
};

export default MunEditor;