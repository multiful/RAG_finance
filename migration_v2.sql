-- Add processing_status to documents table if it doesn't exist
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'documents' AND column_name = 'processing_status') THEN
        ALTER TABLE public.documents ADD COLUMN processing_status text DEFAULT 'pending';
    END IF;
END $$;

-- Add chunks_count to documents table
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'documents' AND column_name = 'chunks_count') THEN
        ALTER TABLE public.documents ADD COLUMN chunks_count integer DEFAULT 0;
    END IF;
END $$;

-- Add last_processed_at to documents table
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'documents' AND column_name = 'last_processed_at') THEN
        ALTER TABLE public.documents ADD COLUMN last_processed_at timestamp with time zone;
    END IF;
END $$;

-- Ensure chunks table has metadata column (jsonb)
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chunks' AND column_name = 'metadata') THEN
        ALTER TABLE public.chunks ADD COLUMN metadata jsonb DEFAULT '{}'::jsonb;
    END IF;
END $$;

-- Update existing documents status to match processing_status
UPDATE public.documents SET processing_status = 'indexed' WHERE status = 'indexed' AND processing_status = 'pending';
