/**
 * 정규표현식 테스트 페이지
 * 각 민감정보 탐지 패턴을 테스트할 수 있는 페이지
 */
import { useState, useEffect, useCallback } from 'react';
import CommonHeader from '../common/CommonHeader';
import './RegexTestPage.css';

interface TestResult {
  pattern: string;
  matches: string[];
  count: number;
}

export default function RegexTestPage() {
  const [testText, setTestText] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('phone');
  const [results, setResults] = useState<Record<string, TestResult>>({});

  // 정규표현식 패턴 정의
  const patterns: Record<string, { name: string; regex: RegExp; description: string }> = {
    phone: {
      name: '전화번호',
      regex: /(?<![0-9])(?:\+82[-.\s]?\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}|01[0-9][-.\s]?\d{3,4}[-.\s]?\d{4}|0[2-9]\d?[-\).\s]?\d{3,4}[-.\s]?\d{4}|070[-.\s]?\d{3,4}[-.\s]?\d{4}|080[-.\s]?\d{3,4}[-.\s]?\d{4}|050[-.\s]?\d{3,4}[-.\s]?\d{4}|1588[-.\s]?\d{4}|1544[-.\s]?\d{4}|1566[-.\s]?\d{4}|1577[-.\s]?\d{4}|1599[-.\s]?\d{4}|1600[-.\s]?\d{4})(?![0-9])/g,
      description: '모바일/지역번호/단축번호 +82 포함 (앞뒤 숫자 제외)'
    },
    rrn: {
      name: '주민등록번호',
      regex: /\d{6}-?\d{7}/g,
      description: '6자리-7자리 형식'
    },
    passport: {
      name: '여권번호',
      regex: /(?:[A-Za-z]\d{3}[A-Za-z]\d{4}|[A-Za-z]\d{8}|[A-Za-z]{2}\d{7})/gi,
      description: '영문+숫자 조합'
    },
    ip_address: {
      name: 'IP주소',
      regex: /(?:(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)){3}|(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4})/g,
      description: 'IPv4 및 IPv6'
    },
    email: {
      name: '이메일',
      regex: /(?:[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})/g,
      description: '이메일 주소 형식'
    },
    account: {
      name: '계좌번호',
      regex: /\b\d{2,6}[-\s]\d{2,6}[-\s]\d{2,7}\b/g,
      description: '은행 포맷 (2~6자리)-(2~6자리)-(2~7자리)'
    },
    school: {
      name: '학교명',
      regex: /(?:[가-힣]{2,}(?:초등학교|중학교|고등학교|대학교)|[가-힣]{2,}(?:고교|대학|여대))/g,
      description: '초등학교, 중학교, 고등학교, 대학교 등'
    },
    address: {
      name: '주소',
      regex: /(?:[가-힣]{2,}(?:특별시|광역시|특별자치도|특별자치시|시|군|구|읍|면|동|리)|\d{1,4}(?:-\d{1,4})?번지|[가-힣]+(?:로|길|대로)\s?\d{1,4}(?:-\d{1,4})?|\d+(?:-\d+)?길|[가-힣]+역|서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)/g,
      description: '시/군/구/읍/면/동/리, 번지, 로/길, 주요 도시명'
    }
  };

  // 테스트 실행
  const runTest = useCallback(() => {
    if (!testText.trim()) {
      setResults({});
      return;
    }

    const newResults: Record<string, TestResult> = {};

    // 선택된 카테고리만 테스트
    if (selectedCategory === 'all') {
      // 모든 패턴 테스트
      Object.entries(patterns).forEach(([key, pattern]) => {
        const matches = testText.match(pattern.regex) || [];
        newResults[key] = {
          pattern: pattern.regex.source,
          matches: matches,
          count: matches.length
        };
      });
    } else {
      // 선택된 패턴만 테스트
      const pattern = patterns[selectedCategory];
      if (pattern) {
        const matches = testText.match(pattern.regex) || [];
        newResults[selectedCategory] = {
          pattern: pattern.regex.source,
          matches: matches,
          count: matches.length
        };
      }
    }

    setResults(newResults);
  }, [testText, selectedCategory]);

  // 텍스트 변경 시 자동 테스트
  useEffect(() => {
    runTest();
  }, [runTest]);

  // 하이라이트된 텍스트 생성
  const getHighlightedText = (category: string) => {
    if (!testText || !results[category]) return testText;
    
    const pattern = patterns[category];
    if (!pattern) return testText;

    let highlighted = testText;
    const matches = results[category].matches;
    
    // 뒤에서부터 마킹하여 인덱스 유지
    matches.slice().reverse().forEach(match => {
      const index = highlighted.lastIndexOf(match);
      if (index !== -1) {
        highlighted = 
          highlighted.substring(0, index) +
          `<mark class="highlight-${category}">${match}</mark>` +
          highlighted.substring(index + match.length);
      }
    });

    return highlighted;
  };

  return (
    <div className="regex-test-page">
      <CommonHeader />
      
      <main className="test-main">
        <div className="test-container">
          <div className="test-header">
            <h1>정규표현식 테스트</h1>
            <p className="subtitle">민감정보 탐지 패턴을 테스트할 수 있습니다</p>
          </div>

          <div className="test-controls">
            <div className="control-group">
              <label htmlFor="category-select">테스트할 패턴:</label>
              <select
                id="category-select"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="category-select"
              >
                <option value="all">전체 패턴</option>
                {Object.entries(patterns).map(([key, pattern]) => (
                  <option key={key} value={key}>
                    {pattern.name} - {pattern.description}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="test-input-section">
            <label htmlFor="test-text">테스트 텍스트:</label>
            <textarea
              id="test-text"
              value={testText}
              onChange={(e) => setTestText(e.target.value)}
              placeholder="테스트할 텍스트를 입력하세요..."
              className="test-textarea"
              rows={8}
            />
          </div>

          <div className="test-results">
            {selectedCategory === 'all' ? (
              // 전체 결과
              <div className="results-grid">
                {Object.entries(patterns).map(([key, pattern]) => {
                  const result = results[key];
                  return (
                    <div key={key} className="result-card">
                      <div className="result-header">
                        <h3>{pattern.name}</h3>
                        <span className={`result-badge ${result?.count ? 'has-matches' : 'no-matches'}`}>
                          {result?.count || 0}개 탐지
                        </span>
                      </div>
                      <p className="pattern-description">{pattern.description}</p>
                      <div className="pattern-regex">
                        <code>{pattern.regex.source}</code>
                      </div>
                      {result && result.matches.length > 0 && (
                        <div className="matches-list">
                          <strong>탐지된 항목:</strong>
                          <ul>
                            {result.matches.map((match, idx) => (
                              <li key={idx}>{match}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {result && (
                        <div 
                          className="highlighted-text"
                          dangerouslySetInnerHTML={{ __html: getHighlightedText(key) }}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              // 선택된 패턴 결과
              <div className="result-detail">
                {results[selectedCategory] ? (
                  <>
                    <div className="result-summary">
                      <h2>{patterns[selectedCategory].name}</h2>
                      <p className="pattern-description">{patterns[selectedCategory].description}</p>
                      <div className="pattern-regex">
                        <strong>정규표현식:</strong>
                        <code>{patterns[selectedCategory].regex.source}</code>
                      </div>
                      <div className="match-count">
                        <strong>탐지된 항목 수:</strong> {results[selectedCategory].count}개
                      </div>
                    </div>
                    
                    {results[selectedCategory].matches.length > 0 && (
                      <div className="matches-section">
                        <h3>탐지된 항목:</h3>
                        <ul className="matches-list">
                          {results[selectedCategory].matches.map((match, idx) => (
                            <li key={idx} className="match-item">
                              <span className="match-index">{idx + 1}</span>
                              <span className="match-value">{match}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className="highlighted-section">
                      <h3>하이라이트된 텍스트:</h3>
                      <div 
                        className="highlighted-text"
                        dangerouslySetInnerHTML={{ __html: getHighlightedText(selectedCategory) }}
                      />
                    </div>
                  </>
                ) : (
                  <div className="no-results">
                    <p>탐지된 항목이 없습니다.</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

