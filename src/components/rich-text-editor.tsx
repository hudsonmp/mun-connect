"use client"

import { useRef, useState, useEffect } from 'react'
import { Editor } from '@tinymce/tinymce-react'
import { useToast } from "@/components/ui/use-toast"

interface RichTextEditorProps {
  initialValue?: string
  onChange?: (content: string) => void
  height?: number
  placeholder?: string
  className?: string
  minimal?: boolean
}

export function RichTextEditor({
  initialValue = '',
  onChange,
  height = 500,
  placeholder = 'Start typing...',
  className,
  minimal = false
}: RichTextEditorProps) {
  const editorRef = useRef<any>(null)
  const [content, setContent] = useState(initialValue)
  const [editorInitialized, setEditorInitialized] = useState(false)
  const [editorError, setEditorError] = useState<string | null>(null)
  const { toast } = useToast()
  
  // Get TinyMCE API key from environment variables
  const tinymceApiKey = process.env.NEXT_PUBLIC_TINYMCE_KEY || '';
  
  useEffect(() => {
    if (!tinymceApiKey) {
      console.error('TinyMCE API key is missing');
      setEditorError('TinyMCE API key is missing');
      toast({
        title: "Editor Configuration Error",
        description: "The text editor could not be initialized due to a configuration error.",
        variant: "destructive",
      });
    }
  }, [tinymceApiKey, toast]);

  const handleEditorChange = (content: string) => {
    setContent(content)
    if (onChange) {
      onChange(content)
    }
  }
  
  const handleInit = (evt: any, editor: any) => {
    editorRef.current = editor
    setEditorInitialized(true)
    console.log('TinyMCE initialized successfully')
  }
  
  const handleInitError = (error: Error) => {
    console.error('TinyMCE initialization error:', error)
    setEditorError(error.message || 'Failed to initialize the editor')
    toast({
      title: "Editor Error",
      description: "There was a problem loading the text editor. Please refresh the page and try again.",
      variant: "destructive",
    })
  }

  if (editorError) {
    return (
      <div className={`border rounded-md p-4 ${className}`}>
        <p className="text-destructive">Error loading the editor: {editorError}</p>
        <p className="text-muted-foreground mt-2">Please check your internet connection and refresh the page.</p>
      </div>
    );
  }

  // Configure editor based on minimal mode
  const plugins = minimal
    ? ['autolink', 'lists', 'link', 'charmap', 'preview', 'searchreplace', 'wordcount']
    : ['advlist', 'autolink', 'lists', 'link', 'image', 'charmap', 'preview',
       'anchor', 'searchreplace', 'visualblocks', 'code', 'fullscreen',
       'insertdatetime', 'media', 'table', 'code', 'help', 'wordcount',
       'exportpdf', 'exportword'];
       
  const toolbar = minimal
    ? 'bold italic | bullist numlist | link | removeformat'
    : 'undo redo | formatselect | bold italic forecolor | alignleft aligncenter ' +
      'alignright alignjustify | bullist numlist outdent indent | ' +
      'removeformat | help | exportpdf exportword';
      
  const menubar = !minimal;

  return (
    <div className={className}>
      <Editor
        apiKey={tinymceApiKey}
        onInit={handleInit}
        initialValue={initialValue}
        init={{
          height,
          menubar,
          plugins,
          toolbar,
          content_style: 'body { font-family:Helvetica,Arial,sans-serif; font-size:14px }',
          placeholder,
          exportpdf_converter_options: {
            format: 'Letter',
            margin_top: '1in',
            margin_right: '1in',
            margin_bottom: '1in',
            margin_left: '1in'
          },
          setup: function(editor: any) {
            editor.on('error', function(e: any) {
              console.error('TinyMCE error:', e);
            });
          }
        }}
        onEditorChange={handleEditorChange}
      />
    </div>
  )
} 