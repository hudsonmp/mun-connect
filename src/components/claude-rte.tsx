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
import axios from 'axios';

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

const MunEditor = () => {
  const editorRef = useRef(null);
  const [content, setContent] = useState('');
  const [documentTitle, setDocumentTitle] = useState('Untitled Document');
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

  // Load initial content or previous version
  useEffect(() => {
    // In a real app, you would fetch from backend
    const savedContent = localStorage.getItem('munEditorContent');
    if (savedContent) {
      setContent(savedContent);
    }
    
    // Mock version history
    setVersionHistory([
      { id: 1, timestamp: new Date().toISOString(), title: 'Initial draft' }
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

  const addCitation = () => {
    const citation = generateCitation(citationData.type, citationData);
    setCitations([...citations, citation]);
    
    // Insert citation reference in editor
    if (editorRef.current) {
      const citationIndex = citations.length + 1;
      editorRef.current.insertContent(`<sup>[${citationIndex}]</sup>`);
    }
    
    setShowCitationDialog(false);
  };

  const generateBibliography = () => {
    if (editorRef.current) {
      let bibliography = '<h2>Bibliography</h2><ol>';
      citations.forEach(citation => {
        bibliography += `<li>${citation}</li>`;
      });
      bibliography += '</ol>';
      
      editorRef.current.insertContent(bibliography);
    }
  };

  const updateHeaderFooter = () => {
    // In a real implementation, this would update the actual document header/footer
    // For TinyMCE, you might need a plugin or custom implementation
    alert('Header and footer settings updated');
  };

  const getAISuggestions = async () => {
    setIsProcessingAI(true);
    try {
      // In a real app, you would call your AI service
      // const response = await axios.post('/api/ai-suggestions', { content });
      
      // Mock AI response for demo
      setTimeout(() => {
        setAiSuggestion("Consider strengthening your position statement on climate action by referencing the latest IPCC report. Also, your economic impact analysis could benefit from more specific data points.");
        setIsProcessingAI(false);
      }, 2000);
    } catch (error) {
      console.error('Error getting AI suggestions:', error);
      setIsProcessingAI(false);
    }
  };

  return (
    <div className="flex flex-col h-full max-w-6xl mx-auto p-4">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <Input 
            value={documentTitle} 
            onChange={(e) => setDocumentTitle(e.target.value)}
            className="text-lg font-bold w-64"
          />
          <span className="text-sm text-gray-500">Version {currentVersion}</span>
        </div>
        <div className="flex items-center gap-2">
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
          <Button onClick={saveVersion}>Save Version</Button>
        </div>
      </div>

      <Tabs defaultValue="editor" className="flex flex-col flex-grow">
        <TabsList>
          <TabsTrigger value="editor">Editor</TabsTrigger>
          <TabsTrigger value="settings">Document Settings</TabsTrigger>
          <TabsTrigger value="ai">AI Assistant</TabsTrigger>
        </TabsList>
        
        <TabsContent value="editor" className="flex-grow">
          <Card className="flex flex-col h-full">
            <CardContent className="pt-4 flex-grow">
              <Editor
                onInit={(evt, editor) => editorRef.current = editor}
                initialValue={content}
                value={content}
                onEditorChange={handleEditorChange}
                init={{
                  height: '100%',
                  menubar: true,
                  plugins: [
                    'advlist', 'autolink', 'lists', 'link', 'image', 'charmap',
                    'anchor', 'searchreplace', 'visualblocks', 'code', 'fullscreen',
                    'insertdatetime', 'media', 'table', 'preview', 'help', 'wordcount',
                    'save', 'autosave'
                  ],
                  toolbar: 'undo redo | blocks fontfamily fontsize | ' +
                    'bold italic underline strikethrough | link image media table | ' +
                    'align lineheight | numlist bullist indent outdent | ' +
                    'removeformat | help',
                  font_formats: 'Arial=arial,helvetica,sans-serif; Times New Roman=times new roman,times,serif;',
                  content_style: 'body { font-family:Times New Roman,Times,serif; font-size:16px }'
                }}
              />
            </CardContent>
            <CardFooter className="flex justify-between">
              <div>
                <Dialog open={showCitationDialog} onOpenChange={setShowCitationDialog}>
                  <DialogTrigger asChild>
                    <Button variant="outline">Add Citation</Button>
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
                <Button variant="outline" className="ml-2" onClick={generateBibliography}>
                  Generate Bibliography
                </Button>
              </div>
            </CardFooter>
          </Card>
        </TabsContent>
        
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
        
        <TabsContent value="ai">
          <Card>
            <CardHeader>
              <CardTitle>AI Writing Assistant</CardTitle>
              <CardDescription>
                Get suggestions to improve your document
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button 
                onClick={getAISuggestions} 
                disabled={isProcessingAI}
              >
                {isProcessingAI ? 'Processing...' : 'Analyze Document'}
              </Button>
              
              {aiSuggestion && (
                <div className="mt-4 p-4 bg-blue-50 rounded-md border border-blue-200">
                  <h3 className="text-sm font-medium mb-2">AI Suggestions:</h3>
                  <p>{aiSuggestion}</p>
                </div>
              )}
              
              <div className="mt-4">
                <h3 className="text-sm font-medium mb-2">Common MUN Phrases</h3>
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
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default MunEditor;