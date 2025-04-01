// Writing styles and formatting
export interface WritingStyle {
  id: string;
  name: string;
  description: string;
  characteristics: string[];
}

export interface FormatStyle {
  id: string;
  name: string;
  description: string;
}

export interface DetailLevel {
  id: string;
  name: string;
  description: string;
}

// Topics categorization
export interface TopicsCollection {
  peaceSecurity: string[];
  humanRights: string[];
  economic: string[];
  environmental: string[];
  healthSocial: string[];
  technology: string[];
}

// Committees categorization
export interface CommitteesCollection {
  generalAssemblies: string[];
  ecosoc: string[];
  specializedAgencies: string[];
  crisisCommittees: string[];
  regional: string[];
}

// User profiles
export interface UserWritingProfile {
  id: string;
  userId: string;
  preferredStyle: string;
  preferredFormat: string;
  detailLevel: string;
  preferredTopics: string[];
  preferredCountries: string[];
  createdAt: string;
  updatedAt: string;
}

// Document creation flow
export interface DocumentSession {
  id: string;
  userId: string;
  committee: string;
  country: string;
  topic: string;
  additionalInfo: string;
  backgroundGuideUrl?: string;
  formattingGuideUrl?: string;
  createdAt: string;
  updatedAt: string;
  status: 'draft' | 'processing' | 'completed';
}

export interface MindMapData {
  keyIssues: string[];
  subtopics: {
    name: string;
    description: string;
    points: string[];
  }[];
  historicalContext: string[];
  potentialSolutions: string[];
  countriesMentioned: string[];
} 