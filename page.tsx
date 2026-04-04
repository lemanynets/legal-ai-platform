"use client";

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { getCase, type CaseDetail, analyzeIntake } from '@/lib/api';
import { getToken, getUserId } from '@/lib/auth';
import { getErrorMessage } from '@/lib/api';

export default function CaseDetailPage() {
    const params = useParams();
    const caseId = params.id as string;

    const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [fileToUpload, setFileToUpload] = useState<File | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [uploading, setUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const fetchCase = async () => {
        setLoading(true);
        setError('');
        try {
            const fetchedCase = await getCase(caseId, getToken(), getUserId());
            setCaseDetail(fetchedCase);
        } catch (err) {
            setError(getErrorMessage(err));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (caseId) {
            void fetchCase();
        }
    }, [caseId]);

    const handleUploadDocument = async () => {
        if (!fileToUpload || !caseId) return;

        setUploading(true);
        setError('');
        try {
            await analyzeIntake(
                { file: fileToUpload, case_id: caseId, jurisdiction: 'UA' },
                getToken(),
                getUserId()
            );
            setFileToUpload(null);
            if (fileInputRef.current) fileInputRef.current.value = "";
            await fetchCase();
        } catch (err) {
            setError(`Помилка завантаження: ${getErrorMessage(err)}`);
        } finally {
            setUploading(false);
        }
    };

    const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
            setIsDragging(true);
        }
    };

    const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    };

    const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const handleDrop = (e: DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            setFileToUpload(e.dataTransfer.files[0]);
            setError('');
            if (fileInputRef.current) fileInputRef.current.value = "";
        }
    };

    if (loading) {
        return <div>Завантаження картки справи...</div>;
    }

    if (error) {
        return <div className="preflight-block" style={{ background: 'var(--danger-bg)', color: 'var(--danger)' }}>{error}</div>;
    }

    if (!caseDetail) {
        return <div>Справу не знайдено.</div>;
    }

    return (
        <div className="animate-fade-in">
            <div className="section-header">
                <div>
                    <h1 className="section-title">{caseDetail.title}</h1>
                    <p className="section-subtitle">
                        Картка справи № {caseDetail.case_number || 'б/н'}
                        <span className="badge badge-muted" style={{ marginLeft: '12px' }}>{caseDetail.status}</span>
                    </p>
                </div>
                <Link href="/dashboard/cases" className="btn btn-secondary">
                    &larr; До списку справ
                </Link>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    <div className="card-elevated" style={{ padding: '24px' }}>
                        <h3 style={{ fontSize: '18px', marginBottom: '12px' }}>Опис справи</h3>
                        <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                            {caseDetail.description || 'Детальний опис справи відсутній.'}
                        </p>
                    </div>

                    <div
                        className="card-elevated"
                        style={{
                            padding: '24px',
                            border: isDragging ? '2px dashed var(--accent)' : '2px dashed transparent',
                            transition: 'border 0.2s ease-in-out',
                            position: 'relative',
                            background: isDragging ? 'rgba(59, 130, 246, 0.05)' : 'var(--card-bg)'
                        }}
                        onDragEnter={handleDragEnter}
                        onDragLeave={handleDragLeave}
                        onDragOver={handleDragOver}
                        onDrop={handleDrop}
                    >
                        {isDragging && (
                            <div style={{
                                position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                                background: 'rgba(59, 130, 246, 0.1)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                color: 'var(--accent)', fontWeight: 'bold', fontSize: '18px',
                                borderRadius: '24px',
                                pointerEvents: 'none'
                            }}>
                                Перетягніть файл сюди
                            </div>
                        )}
                        <h3 style={{ fontSize: '18px', marginBottom: '12px' }}>Додати документ до справи</h3>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '-8px', marginBottom: '16px' }}>
                            Перетягніть файл у цю область або оберіть його вручну.
                        </p>
                        <input
                            type="file"
                            id="file-upload-case"
                            ref={fileInputRef}
                            className="form-input"
                            style={{ display: 'none' }}
                            onChange={(e) => {
                                setFileToUpload(e.target.files?.[0] || null);
                                setError('');
                            }}
                        />
                        {fileToUpload && (
                            <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px 16px', borderRadius: '12px', marginBottom: '16px', fontSize: '14px', color: 'var(--text-secondary)' }}>
                                Обрано файл: <strong style={{ color: '#fff' }}>{fileToUpload.name}</strong>
                            </div>
                        )}
                        <label htmlFor="file-upload-case" className="btn btn-secondary" style={{ marginRight: '12px', cursor: 'pointer' }}>
                            Обрати файл
                        </label>
                        <button
                            className="btn btn-primary"
                            onClick={handleUploadDocument}
                            disabled={!fileToUpload || uploading}
                        >
                            {uploading ? 'Завантаження...' : 'Завантажити та проаналізувати'}
                        </button>
                    </div>

                    <div className="card-elevated" style={{ padding: '24px' }}>
                        <h3 style={{ fontSize: '18px', marginBottom: '12px' }}>Документи по справі ({caseDetail.documents.length})</h3>
                        {caseDetail.documents.length > 0 ? (
                            <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                {caseDetail.documents.map(doc => (
                                    <li key={doc.id} className="card-hover" style={{ background: 'rgba(255,255,255,0.03)', padding: '12px 16px', borderRadius: '12px' }}>
                                        <Link href={`/dashboard/documents/${doc.id}`} style={{ textDecoration: 'none', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <div>
                                                <span style={{ fontWeight: 600, color: '#fff' }}>{doc.document_category}</span>
                                                <span className="badge badge-muted" style={{ marginLeft: '8px' }}>{doc.document_type}</span>
                                            </div>
                                            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                                                {new Date(doc.created_at).toLocaleDateString()}
                                            </span>
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p style={{ color: 'var(--text-muted)' }}>Документи до цієї справи ще не додано.</p>
                        )}
                    </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    <div className="card-elevated" style={{ padding: '24px' }}>
                        <h3 style={{ fontSize: '18px', marginBottom: '12px' }}>Ключова інформація</h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '14px' }}>
                            <div>
                                <strong style={{ color: 'var(--text-muted)', display: 'block', fontSize: '12px' }}>ID Справи:</strong>
                                <code style={{ color: 'var(--gold-400)' }}>{caseDetail.id}</code>
                            </div>
                            <div>
                                <strong style={{ color: 'var(--text-muted)', display: 'block', fontSize: '12px' }}>Створено:</strong>
                                <span>{new Date(caseDetail.created_at).toLocaleString()}</span>
                            </div>
                            <div>
                                <strong style={{ color: 'var(--text-muted)', display: 'block', fontSize: '12px' }}>Оновлено:</strong>
                                <span>{new Date(caseDetail.updated_at).toLocaleString()}</span>
                            </div>
                        </div>
                    </div>

                    <div className="card-elevated" style={{ padding: '24px' }}>
                        <h3 style={{ fontSize: '18px', marginBottom: '12px' }}>Обговорення ({caseDetail.forum_posts.length})</h3>
                        {caseDetail.forum_posts.length > 0 ? (
                            <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                {caseDetail.forum_posts.map(post => (
                                    <li key={post.id} className="card-hover" style={{ background: 'rgba(255,255,255,0.03)', padding: '12px 16px', borderRadius: '12px' }}>
                                        <Link href={`/dashboard/forum/${post.id}`} style={{ textDecoration: 'none' }}>
                                            <span style={{ fontWeight: 600, color: '#fff' }}>{post.title}</span>
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p style={{ color: 'var(--text-muted)' }}>Обговорення по цій справі ще не розпочато.</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}