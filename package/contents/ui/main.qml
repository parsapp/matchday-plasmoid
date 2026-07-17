import QtQuick
import QtQuick.Layouts
import org.kde.plasma.components as PC3
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: root

    property string dataUrl: "https://raw.githubusercontent.com/parsapp/pars-plasmoid/main/data/worldcup.json"
    property string title: "Yükleniyor..."
    property string nextText: ""

    ListModel { id: matchModel }

    function refresh() {
        const xhr = new XMLHttpRequest()
        xhr.onreadystatechange = function() {
            if (xhr.readyState !== XMLHttpRequest.DONE) return
            if (xhr.status !== 200) { root.title = "Veri alinamadi"; return }
            try {
                const data = JSON.parse(xhr.responseText)
                root.title = "⚽ " + data.league
                root.nextText = data.next ? data.next : ""
                matchModel.clear()
                for (const m of data.matches) {
                    matchModel.append({ home: m.home, away: m.away, score: m.score, info: m.info })
                }
            } catch (e) { root.title = "Veri bozuk" }
        }
        xhr.open("GET", root.dataUrl)
        xhr.send()
    }

    Component.onCompleted: refresh()
    Timer { interval: 1800000; running: true; repeat: true; onTriggered: root.refresh() }

    compactRepresentation: MouseArea {
        implicitWidth: compactRow.implicitWidth + 12
        implicitHeight: compactRow.implicitHeight
        onClicked: root.expanded = !root.expanded

        RowLayout {
            id: compactRow
            anchors.centerIn: parent
            spacing: 4
            PC3.Label { text: "⚽" }
            PC3.Label { text: root.nextText; visible: root.nextText !== "" }
        }
    }

    fullRepresentation: ColumnLayout {
        spacing: 8
        Layout.minimumWidth: 300
        Layout.minimumHeight: 360

        PC3.Label {
            text: root.title
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: matchModel
            spacing: 10
            clip: true

            delegate: Column {
                width: ListView.view.width
                spacing: 2

                RowLayout {
                    width: parent.width
                    PC3.Label { text: home; Layout.fillWidth: true; elide: Text.ElideRight }
                    PC3.Label { text: score; font.bold: true }
                    PC3.Label { text: away; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight }
                }
                PC3.Label {
                    text: info
                    opacity: 0.6
                    font.pointSize: 8
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
        }
    }
}
