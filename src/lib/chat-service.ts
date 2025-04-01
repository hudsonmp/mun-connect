import { v4 as uuidv4 } from 'uuid';
import supabase from './supabase-client';

// Types
export interface Message {
  id: string;
  type: 'user' | 'system' | 'editor' | 'upload' | 'error';
  content: string;
  timestamp: Date;
  documentId?: string;
  documentType?: 'position_paper' | 'resolution' | 'speech';
  files?: File[];
}

export interface Chat {
  id: string;
  userId: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  messages: Message[];
}

// Function to create a new chat session
export async function createChat(userId: string, title: string = 'New Chat'): Promise<{ chat: Chat | null; error: Error | null }> {
  try {
    const chatId = uuidv4();
    
    const { data, error } = await supabase
      .from('chats')
      .insert([
        { 
          id: chatId,
          user_id: userId,
          title
        }
      ])
      .select()
      .single();
      
    if (error) throw error;
    
    return { 
      chat: {
        id: data.id,
        userId: data.user_id,
        title: data.title,
        createdAt: new Date(data.created_at),
        updatedAt: new Date(data.updated_at),
        messages: []
      }, 
      error: null 
    };
  } catch (error) {
    console.error('Error creating chat:', error);
    return { chat: null, error: error as Error };
  }
}

// Function to save messages to a chat
export async function saveMessages(chatId: string, messages: Message[]): Promise<{ success: boolean; error: Error | null }> {
  try {
    // First, delete any existing messages for this chat to avoid duplicates
    const { error: deleteError } = await supabase
      .from('messages')
      .delete()
      .eq('chat_id', chatId);
      
    if (deleteError) throw deleteError;
    
    // Format messages for Supabase
    const messagesToInsert = messages.map((msg, index) => ({
      id: msg.id,
      chat_id: chatId,
      role: msg.type,
      content: JSON.stringify({
        content: msg.content,
        documentId: msg.documentId,
        documentType: msg.documentType,
        // We can't store File objects directly, so we'll omit them in storage
      }),
      order_index: index
    }));
    
    // Insert all messages
    const { error: insertError } = await supabase
      .from('messages')
      .insert(messagesToInsert);
      
    if (insertError) throw insertError;
    
    // Update the chat's updated_at timestamp
    const { error: updateError } = await supabase
      .from('chats')
      .update({ updated_at: new Date().toISOString() })
      .eq('id', chatId);
      
    if (updateError) throw updateError;
    
    return { success: true, error: null };
  } catch (error) {
    console.error('Error saving messages:', error);
    return { success: false, error: error as Error };
  }
}

// Function to load a chat and its messages
export async function loadChat(chatId: string): Promise<{ chat: Chat | null; error: Error | null }> {
  try {
    // Get the chat details
    const { data: chatData, error: chatError } = await supabase
      .from('chats')
      .select('*')
      .eq('id', chatId)
      .single();
      
    if (chatError) throw chatError;
    
    // Get the messages for this chat
    const { data: messageData, error: messageError } = await supabase
      .from('messages')
      .select('*')
      .eq('chat_id', chatId)
      .order('order_index', { ascending: true });
      
    if (messageError) throw messageError;
    
    // Parse and format the messages
    const messages = messageData.map(msg => {
      const parsedContent = JSON.parse(msg.content);
      return {
        id: msg.id,
        type: msg.role,
        content: parsedContent.content,
        timestamp: new Date(msg.created_at),
        documentId: parsedContent.documentId,
        documentType: parsedContent.documentType
      } as Message;
    });
    
    // Return the complete chat
    return {
      chat: {
        id: chatData.id,
        userId: chatData.user_id,
        title: chatData.title,
        createdAt: new Date(chatData.created_at),
        updatedAt: new Date(chatData.updated_at),
        messages
      },
      error: null
    };
  } catch (error) {
    console.error('Error loading chat:', error);
    return { chat: null, error: error as Error };
  }
}

// Function to list all chats for a user
export async function listUserChats(userId: string): Promise<{ chats: Chat[] | null; error: Error | null }> {
  try {
    const { data, error } = await supabase
      .from('chats')
      .select('*')
      .eq('user_id', userId)
      .order('updated_at', { ascending: false });
      
    if (error) throw error;
    
    const chats = data.map(chat => ({
      id: chat.id,
      userId: chat.user_id,
      title: chat.title,
      createdAt: new Date(chat.created_at),
      updatedAt: new Date(chat.updated_at),
      messages: [] // We don't load messages in the list view for efficiency
    }));
    
    return { chats, error: null };
  } catch (error) {
    console.error('Error listing chats:', error);
    return { chats: null, error: error as Error };
  }
}

// Function to delete a chat
export async function deleteChat(chatId: string): Promise<{ success: boolean; error: Error | null }> {
  try {
    // Due to CASCADE delete, we only need to delete the chat
    const { error } = await supabase
      .from('chats')
      .delete()
      .eq('id', chatId);
      
    if (error) throw error;
    
    return { success: true, error: null };
  } catch (error) {
    console.error('Error deleting chat:', error);
    return { success: false, error: error as Error };
  }
} 