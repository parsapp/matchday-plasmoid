import QtQuick
import QtQuick.Layouts
import org.kde.plasma.components as PC3
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: root

    ListModel {
        id: matchModel
        ListElement { home: "Galatasaray"; away: "Fenerbahçe"; score: "2 - 1"; info: "Oynandı · 12 Tem" }
        ListElement { home: "Beşiktaş"; away: "Trabzonspor"; score: "0 - 0"; info: "Oynandı · 13 Tem" }
        ListElement { home: "Samsunspor"; away: "Göztepe"; score: "–"; info: "19 Tem 20:00" }
        ListElement { home: "Kasımpaşa"; away: "Konyaspor"; score: "–"; info: "20 Tem 18:30" }
        ListElement { home: "Rizespor"; away: "Antalyaspor"; score: "–"; info: "20 Tem 21:00" }
    }

    fullRepresentation: ColumnLayout {
        spacing: 8
        Layout.minimumWidth: 300
        Layout.minimumHeight: 340

        PC3.Label {
            text: "⚽ Süper Lig"
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
