import React from 'react';
import { Button } from '../../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { GoogleLogo, Presentation, Article } from '@phosphor-icons/react';

export function GoogleImportDialog({
  importOpen, importTab, googleSlides, googleDocs, importing,
  onClose, onSetTab, onImportSlide, onImportDoc,
}) {
  return (
    <Dialog open={importOpen !== null} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="bg-[#0F172A] border-[#1E293B] max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-[#F8FAFC] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            <GoogleLogo size={20} className="text-[#D4AF37]" /> Import from Google
          </DialogTitle>
        </DialogHeader>

        <div className="flex gap-1 p-1 bg-[#050814] border border-[#1E293B] rounded-md mb-4">
          <button
            onClick={() => onSetTab('slides')}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded transition-all ${
              importTab === 'slides' ? 'bg-[#D4AF37] text-[#050814]' : 'text-[#94A3B8] hover:text-[#F8FAFC]'
            }`}
            data-testid="import-tab-slides"
          >
            <Presentation size={14} /> Slides
          </button>
          <button
            onClick={() => onSetTab('docs')}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded transition-all ${
              importTab === 'docs' ? 'bg-[#D4AF37] text-[#050814]' : 'text-[#94A3B8] hover:text-[#F8FAFC]'
            }`}
            data-testid="import-tab-docs"
          >
            <Article size={14} /> Docs
          </button>
        </div>

        <div className="space-y-2">
          {importTab === 'slides' && (
            googleSlides.length === 0 ? (
              <p className="text-sm text-[#94A3B8] text-center py-4">No Google Slides found in your account.</p>
            ) : (
              googleSlides.map(slide => (
                <div
                  key={slide.id}
                  className="flex items-center gap-3 p-3 bg-[#050814] border border-[#1E293B] rounded-md hover:border-[#D4AF37]/20 transition-colors"
                  data-testid={`import-slide-${slide.id}`}
                >
                  <Presentation size={20} weight="duotone" className="text-[#D4AF37] flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[#F8FAFC] truncate">{slide.name}</p>
                    <p className="text-[10px] text-[#94A3B8]">Modified {new Date(slide.modifiedTime).toLocaleDateString()}</p>
                  </div>
                  <Button
                    size="sm"
                    onClick={() => onImportSlide(slide.id, importOpen)}
                    className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-[10px]"
                    disabled={importing}
                  >
                    {importing ? 'Importing...' : 'Import'}
                  </Button>
                </div>
              ))
            )
          )}
          {importTab === 'docs' && (
            googleDocs.length === 0 ? (
              <p className="text-sm text-[#94A3B8] text-center py-4">No Google Docs found in your account.</p>
            ) : (
              googleDocs.map(doc => (
                <div
                  key={doc.id}
                  className="flex items-center gap-3 p-3 bg-[#050814] border border-[#1E293B] rounded-md hover:border-[#D4AF37]/20 transition-colors"
                  data-testid={`import-doc-${doc.id}`}
                >
                  <Article size={20} weight="duotone" className="text-[#D4AF37] flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[#F8FAFC] truncate">{doc.name}</p>
                    <p className="text-[10px] text-[#94A3B8]">Modified {new Date(doc.modifiedTime).toLocaleDateString()}</p>
                  </div>
                  <Button
                    size="sm"
                    onClick={() => onImportDoc(doc.id, importOpen)}
                    className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-[10px]"
                    disabled={importing}
                  >
                    {importing ? 'Importing...' : 'Import'}
                  </Button>
                </div>
              ))
            )
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
